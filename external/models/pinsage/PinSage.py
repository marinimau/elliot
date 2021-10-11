"""
Module description:

"""

__version__ = '0.3.0'
__author__ = 'Vito Walter Anelli, Claudio Pomo, Daniele Malitesta, Felice Antonio Merra'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it, daniele.malitesta@poliba.it, felice.merra@poliba.it'

from ast import literal_eval as make_tuple

from tqdm import tqdm
import numpy as np
import networkx as nx

from elliot.dataset.samplers import custom_sampler as cs
from elliot.recommender import BaseRecommenderModel
from elliot.recommender.base_recommender_model import init_charger
from elliot.recommender.recommender_utils_mixin import RecMixin
from .PinSageModel import PinSageModel


class PinSage(RecMixin, BaseRecommenderModel):
    r"""
    Graph Convolutional Neural Networks for Web-Scale Recommender Systems

    For further details, please refer to the `paper <https://dl.acm.org/doi/10.1145/3219819.3219890>`_

    Args:
        lr: Learning rate
        epochs: Number of epochs
        factors: Number of latent factors
        batch_size: Batch size
        l_w: Regularization coefficient
        message_weight_size: Tuple with number of units for each message layer
        convolution_weight_size: Tuple with number of units for each convolution layer
        out_weight_size: Single tuple with number of units for the two output layers
        t_top_nodes: Number of nodes to consider from neighborhood according to L1-norm random walks

    To include the recommendation model, add it to the config file adopting the following pattern:

    .. code:: yaml

      models:
        PinSage:
          meta:
            save_recs: True
          lr: 0.0005
          epochs: 50
          batch_size: 512
          factors: 64
          l_w: 0.1
          message_weight_size: (64,32,32)
          convolution_weight_size: (64,32,32)
          out_weight_size: (64,32)
          t_top_nodes: 10
    """

    @init_charger
    def __init__(self, data, config, params, *args, **kwargs):

        self._sampler = cs.Sampler(self._data.i_train_dict)
        if self._batch_size < 1:
            self._batch_size = self._num_users

        ######################################

        self._params_list = [
            ("_learning_rate", "lr", "lr", 0.0005, None, None),
            ("_factors", "factors", "factors", 64, None, None),
            ("_l_w", "l_w", "l_w", 0.01, None, None),
            ("_message_weight_size", "message_weight_size", "message_weight_size", "(64,)",
             lambda x: list(make_tuple(x)),
             lambda x: self._batch_remove(str(x), " []").replace(",", "-")),
            ("_convolution_weight_size", "convolution_weight_size", "convolution_weight_size", "(64,)",
             lambda x: list(make_tuple(x)),
             lambda x: self._batch_remove(str(x), " []").replace(",", "-")),
            ("_out_weight_size", "out_weight_size", "out_weight_size", "(64,)",
             lambda x: list(make_tuple(x)),
             lambda x: self._batch_remove(str(x), " []").replace(",", "-")),
            ("_t_top_nodes", "t_top_nodes", "t_top_nodes", 10, None, None),
            ("_delta", "delta", "delta", 0.5, None, None),
        ]
        self.autoset_params()

        self._n_layers = len(self._message_weight_size)
        row, col = data.sp_i_train.nonzero()
        col = [c + self._num_users for c in col]
        self.edge_index = np.array([row, col])

        # Build graph with networkx for personalized page rank
        G = nx.Graph()
        G.add_nodes_from(row, bipartite=0)
        G.add_nodes_from(col, bipartite=1)
        G.add_edges_from(list(zip(col, row)))

        self._model = PinSageModel(
            num_users=self._num_users,
            num_items=self._num_items,
            learning_rate=self._learning_rate,
            embed_k=self._factors,
            l_w=self._l_w,
            message_weight_size=self._message_weight_size,
            convolution_weight_size=self._convolution_weight_size,
            out_weight_size=self._out_weight_size,
            t_top_nodes=self._t_top_nodes,
            n_layers=self._n_layers,
            delta=self._delta,
            edge_index=self.edge_index,
            graph=G,
            random_seed=self._seed
        )

    @property
    def name(self):
        return "PinSage" \
               + f"_{self.get_base_params_shortcut()}" \
               + f"_{self.get_params_shortcut()}"

    def train(self):
        if self._restore:
            return self.restore_weights()

        for it in self.iterate(self._epochs):
            loss = 0
            steps = 0
            with tqdm(total=int(self._data.transactions // self._batch_size), disable=not self._verbose) as t:
                for batch in self._sampler.step(self._data.transactions, self._batch_size):
                    steps += 1
                    loss += self._model.train_step(batch)
                    t.set_postfix({'loss': f'{loss / steps:.5f}'})
                    t.update()

            self.evaluate(it, loss / (it + 1))

    def get_recommendations(self, k: int = 100):
        predictions_top_k_test = {}
        predictions_top_k_val = {}
        gu, gi = self._model.propagate_embeddings(evaluate=True)
        for index, offset in enumerate(range(0, self._num_users, self._batch_size)):
            offset_stop = min(offset + self._batch_size, self._num_users)
            predictions = self._model.predict(gu[offset: offset_stop], gi)
            recs_val, recs_test = self.process_protocol(k, predictions, offset, offset_stop)
            predictions_top_k_val.update(recs_val)
            predictions_top_k_test.update(recs_test)
        return predictions_top_k_val, predictions_top_k_test

    def get_single_recommendation(self, mask, k, predictions, offset, offset_stop):
        v, i = self._model.get_top_k(predictions, mask[offset: offset_stop], k=k)
        items_ratings_pair = [list(zip(map(self._data.private_items.get, u_list[0]), u_list[1]))
                              for u_list in list(zip(i.detach().cpu().numpy(), v.detach().cpu().numpy()))]
        return dict(zip(map(self._data.private_users.get, range(offset, offset_stop)), items_ratings_pair))