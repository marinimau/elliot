"""
This is the metrics' module.

This module contains and expose the recommendation metrics.
Each metric is encapsulated in a specific package.

See the implementation of Precision metric for creating new per-user metrics.
See the implementation of Item Coverage for creating new cross-user metrics.
"""

__version__ = '0.1'
__author__ = 'Vito Walter Anelli, Claudio Pomo'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it'

from evaluation.metrics.accuracy.ndcg import NDCG
from evaluation.metrics.accuracy.precision import Precision
from evaluation.metrics.accuracy.recall import Recall
from evaluation.metrics.diversity.item_coverage import ItemCoverage
from evaluation.metrics.fairness.MAD import UserMADrating
from evaluation.metrics.accuracy.hit_rate import HR
from evaluation.metrics.accuracy.mrr import MRR
from evaluation.metrics.accuracy.map import MAP
from evaluation.metrics.rating.mae import MAE
from evaluation.metrics.rating.mse import MSE
from evaluation.metrics.rating.rmse import RMSE
from evaluation.metrics.accuracy.f1 import F1
from evaluation.metrics.accuracy.DSC import DSC
from evaluation.metrics.diversity.gini_index import GiniIndex
from evaluation.metrics.diversity.shannon_entropy import ShannonEntropy
from evaluation.metrics.novelty.EFD import EFD
from evaluation.metrics.novelty.EPC import EPC
from evaluation.metrics.accuracy.AUC import LAUC, AUC, GAUC
from evaluation.metrics.diversity.SRecall import SRecall

from evaluation.metrics.statistical_array_metric import StatisticalMetric

_metric_dictionary = {
    "nDCG": NDCG,
    "Precision": Precision,
    "Recall": Recall,
    "HR": HR,
    "MRR": MRR,
    "MAP": MAP,
    "F1": F1,
    "DSC": DSC,
    "LAUC": LAUC,
    "GAUC": GAUC,
    "AUC": AUC,
    "ItemCoverage": ItemCoverage,
    "Gini": GiniIndex,
    "SEntropy": ShannonEntropy,
    "EFD": EFD,
    "EPC": EPC,
    "MAE": MAE,
    "MSE": MSE,
    "RMSE": RMSE,
    "UserMADrating": UserMADrating,
    "SRecall": SRecall
}


def parse_metrics(metrics):
    return [_metric_dictionary[m] for m in metrics if m in _metric_dictionary.keys()]


def parse_metric(metric):
    return _metric_dictionary[metric] if metric in _metric_dictionary.keys() else None
