import itertools
import time
import os
import glob
import logging
from collections import defaultdict, OrderedDict
from functools import partial

import screed
import numpy as np
from pathos import multiprocessing

from . import tenx_utils
from .bam2fasta_args import create_parser
from . import np_utils


logger = logging.getLogger(__name__)

DELIMITER = "X"
CELL_BARCODE = "CELL_BARCODE"
UMI_COUNT = "UMI_COUNT"
READ_COUNT = "READ_COUNT"


def iter_split(string, sep=None):
    """Split a string by the given separator and
    return the results in a generator"""
    sep = sep or ' '
    groups = itertools.groupby(string, lambda s: s != sep)
    return (''.join(g) for k, g in groups if k)


def calculate_chunksize(total_jobs_todo, processes):
    chunksize, extra = divmod(total_jobs_todo, processes)
    if extra:
        chunksize += 1
    return chunksize


def convert(args):

    parser = create_parser()
    args = parser.parse_args(args)

    logger.info(args)

    umi_filter = True if args.count_valid_reads != 0 else False
    all_fastas_sorted = []
    all_fastas = ""

    def collect_reduce_temp_fastas(index):
        """Convert fasta to sig record"""
        if umi_filter:
            return filtered_umi_to_fasta(index)
        else:
            return unfiltered_umi_to_fasta(index)

    def unfiltered_umi_to_fasta(index):
        """Returns signature records across fasta files for a unique barcode"""

        # Getting all fastas for a given barcode
        # from different shards
        single_barcode_fastas = all_fastas_sorted[index]

        count = 0
        # Iterating through fasta files for single barcode from different
        # fastas
        for fasta in iter_split(single_barcode_fastas, ","):

            # Initializing the fasta file to write
            # all the sequences from all bam shards to
            if count == 0:
                unique_fasta_file = os.path.basename(fasta)
                barcode_name = unique_fasta_file.replace(".fasta", "")
                f = open(os.path.join(args.save_fastas, unique_fasta_file), "w")

            # Add sequence
            for record in screed.open(fasta):
                sequence = record.sequence
                umi = record.name

                split_seqs = sequence.split(args.delimiter)
                for index, seq in enumerate(split_seqs):
                    if seq == "":
                        continue
                    f.write(">{}\n{}\n".format(
                        barcode_name + "_" + umi + "_" + '{:03d}'.format(index), seq))

            # Delete fasta file in tmp folder
            if os.path.exists(fasta):
                os.unlink(fasta)

            count += 1

        # Updating the fasta file with each of the sequences and closing the fasta file
        f.close()

    def filtered_umi_to_fasta(index):
        """Returns signature records for all the fasta files for a unique
        barcode, only if it has more than count-valid-reads number of umis."""

        # Getting all fastas for a given barcode
        # from different shards
        single_barcode_fastas = all_fastas_sorted[index]

        logger.debug("calculating umi counts")
        # Tracking UMI Counts
        umis = defaultdict(int)
        # Iterating through fasta files for single barcode from different
        # fastas
        for fasta in iter_split(single_barcode_fastas, ","):
            # calculate unique umi, sequence counts
            for record in screed.open(fasta):
                umis[record.name] += record.sequence.count(args.delimiter)

        if args.write_barcode_meta_csv:
            unique_fasta_file = os.path.basename(fasta)
            unique_meta_file = unique_fasta_file.replace(".fasta", "_meta.txt")
            with open(unique_meta_file, "w") as f:
                f.write("{} {}".format(len(umis), sum(list(umis.values()))))

        logger.debug("Completed tracking umi counts")
        if len(umis) < args.count_valid_reads:
            return []
        count = 0
        for fasta in iter_split(single_barcode_fastas, ","):

            # Initializing fasta file to save the sequence to
            if count == 0:
                unique_fasta_file = os.path.basename(fasta)
                barcode_name = unique_fasta_file.replace(".fasta", "")
                f = open(os.path.join(args.save_fastas, unique_fasta_file), "w")

            # Add sequences of barcodes with more than count-valid-reads umis
            for record in screed.open(fasta):
                sequence = record.sequence
                umi = record.name

                # Appending sequence of a umi to the fasta
                split_seqs = sequence.split(args.delimiter)
                for index, seq in enumerate(split_seqs):
                    if seq == "":
                        continue
                    f.write(">{}\n{}\n".format(
                        barcode_name + "_" + umi + "_" + '{:03d}'.format(index), seq))
            # Delete fasta file in tmp folder
            if os.path.exists(fasta):
                os.unlink(fasta)
            count += 1

        # Update the fasta file with all sequence and close the opened fasta file
        f.close()

    def write_to_barcode_meta_csv():
        barcodes_meta_txts = glob.glob("*_meta.txt")

        with open(args.write_barcode_meta_csv, "w") as fp:
            fp.write("{},{},{}".format(CELL_BARCODE, UMI_COUNT,
                                       READ_COUNT))
            fp.write('\n')
            for barcode_meta_txt in barcodes_meta_txts:
                with open(barcode_meta_txt, 'r') as f:
                    umi_count, read_count = f.readline().split()
                    umi_count = int(umi_count)
                    read_count = int(read_count)

                    barcode_name = barcode_meta_txt.replace('_meta.txt', '')
                    fp.write("{},{},{}\n".format(barcode_name,
                                                 umi_count,
                                                 read_count))

    def get_unique_barcodes(all_fastas):
        # Build a dictionary with each unique barcode as key and
        # their fasta files from different shards
        fasta_files_dict = OrderedDict()
        for fasta in iter_split(all_fastas, ","):
            barcode = os.path.basename(fasta).replace(".fasta", "")
            value = fasta_files_dict.get(barcode, "")
            fasta_files_dict[barcode] = value + fasta + ","
        # Find unique barcodes
        all_fastas_sorted = list(fasta_files_dict.values())
        del fasta_files_dict
        return all_fastas_sorted

    # Initializing time
    startt = time.time()

    # Setting barcodes file, some 10x files don't have a filtered
    # barcode file
    if args.barcodes_file is not None:
        barcodes = tenx_utils.read_barcodes_file(args.barcodes_file)
    else:
        barcodes = None

    # Shard bam file to smaller bam file
    logger.info('... reading bam file from {}'.format(args.filename))
    n_jobs = args.processes
    filenames, mmap_file = np_utils.to_memmap(np.array(
        tenx_utils.shard_bam_file(
            args.filename,
            args.line_count,
            os.getcwd())))

    # Create a per-cell fasta generator of sequences
    # If the reads should be filtered by barcodes and umis
    # umis are saved in fasta file as record name and name of
    # the fasta file is the barcode
    func = partial(
        tenx_utils.bam_to_temp_fasta,
        barcodes,
        args.rename_10x_barcodes,
        args.delimiter)

    length_sharded_bam_files = len(filenames)
    chunksize = calculate_chunksize(length_sharded_bam_files,
                                    n_jobs)
    pool = multiprocessing.Pool(processes=n_jobs)
    logger.info(
        "multiprocessing pool processes {} and chunksize {} calculated".format(
            n_jobs, chunksize))
    # All the fastas are stored in a string instead of a list
    # This saves memory per element of the list by 8 bits
    # If we have unique barcodes in the order of 10^6 before
    # filtering that would result in a huge list if each barcode
    # is saved as a separate element, hence the string
    all_fastas = "," .join(itertools.chain(*(
        pool.imap(
            lambda x: func(x.encode('utf-8')), filenames, chunksize=chunksize))))
    pool.close()
    pool.join()

    # clean up the memmap and sharded intermediary bam files
    [os.unlink(file) for file in filenames if os.path.exists(file)]
    del filenames
    os.unlink(mmap_file)
    logger.info("Deleted intermediary bam and memmap files")

    all_fastas_sorted = get_unique_barcodes(all_fastas)
    unique_barcodes = len(all_fastas_sorted)
    logger.info("Found %d unique barcodes", unique_barcodes)
    # Cleaning up to retrieve memory from unused large variables
    del all_fastas

    pool = multiprocessing.Pool(processes=n_jobs)
    chunksize = calculate_chunksize(unique_barcodes, n_jobs)
    logger.info("Pooled {} and chunksize {} mapped".format(
        n_jobs, chunksize))

    list(pool.imap(
        lambda index: collect_reduce_temp_fastas(index),
        range(unique_barcodes),
        chunksize=chunksize))

    pool.close()
    pool.join()

    if args.write_barcode_meta_csv:
        write_to_barcode_meta_csv()
    logger.info(
        "time taken to convert fastas for 10x folder is {:.5f} seconds", time.time() - startt)
