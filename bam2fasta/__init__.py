__version__ = '0.2.4dev0'


__title__ = 'bam2fasta'
__description__ = 'Convert bam file to fasta file per cell barcode'
__uri__ = 'https://github.com/czbiohub/bam2fasta'
__doc__ = __description__ + ' <' + __uri__ + '>'

__author__ = 'Pranathi Vemuri'
__email__ = 'pranathi93.vemuri@gmail.com'

__license__ = 'MIT License'
__copyright__ = 'Copyright (c) 2019 Chan Zuckerberg Biohub'


from pkg_resources import get_distribution, DistributionNotFound
try:
    VERSION = get_distribution(__name__).version
except DistributionNotFound:  # pragma: no cover
    try:
        from .version import version as VERSION  # noqa
    except ImportError:  # pragma: no cover
        raise ImportError(
            "Failed to find (autogenerated) version.py. "
            "This might be because you are installing from GitHub's tarballs, "
            "use the PyPI ones."
        )
