"""
Module description:

"""

__version__ = '0.1'
__author__ = 'Vito Walter Anelli, Claudio Pomo, Daniele Malitesta, Felice Antonio Merra'
__email__ = 'vitowalter.anelli@poliba.it, claudio.pomo@poliba.it, daniele.malitesta@poliba.it, felice.merra@poliba.it'

from ast import literal_eval as make_tuple

from tqdm import tqdm

from elliot.recommender import BaseRecommenderModel
from elliot.recommender.base_recommender_model import init_charger
from elliot.recommender.recommender_utils_mixin import RecMixin
from elliot.recommender.visual_recommenders.ACF.ACF_model import ACF_model
from elliot.recommender.visual_recommenders.ACF.pairwise_pipeline_sampler_acf import Sampler as ppsa


class ACF(RecMixin, BaseRecommenderModel):
    r"""
    Attentive Collaborative Filtering: Multimedia Recommendation with Item- and Component-Level Attention

    For further details, please refer to the `paper <https://dl.acm.org/doi/10.1145/3077136.3080797>`_

    Args:
        lr: Learning rate
        epochs: Number of epochs
        factors: Number of latent factors
        batch_size: Batch size
        l_w: Regularization coefficient
        layers_component: Tuple with number of units for each attentive layer (component-level)
        layers_item: Tuple with number of units for each attentive layer (item-level)

    To include the recommendation model, add it to the config file adopting the following pattern:

    .. code:: yaml

      models:
        ACF:
          meta:
            save_recs: True
          lr: 0.0005
          epochs: 50
          factors: 100
          batch_size: 128
          l_w: 0.000025
          layers_component: (64, 1)
          layers_item: (64, 1)
    """
    @init_charger
    def __init__(self, data, config, params, *args, **kwargs):

        self._num_items = self._data.num_items
        self._num_users = self._data.num_users
        self._layers_component = self._params.layers_component
        self._layers_item = self._params.layers_item

        self._params_list = [
            ("_factors", "factors", "factors", 100, None, None),
            ("_learning_rate", "lr", "lr", 0.0005, None, None),
            ("_l_w", "l_w", "l_w", 0.000025, None, None),
            ("_layers_component", "layers_component", "layers_component", "(64,1)", lambda x: list(make_tuple(x)),
             lambda x: self._batch_remove(str(x), " []").replace(",", "-")),
            ("_layers_item", "layers_item", "layers_item", "(64,1)", lambda x: list(make_tuple(x)),
             lambda x: self._batch_remove(str(x), " []").replace(",", "-")),
            ("_loader", "loader", "load", "VisualAttributes", None, None),
        ]

        self.autoset_params()

        if self._batch_size < 1:
            self._batch_size = self._data.transactions

        self._side = getattr(self._data.side_information, self._loader, None)

        self._sampler = ppsa.Sampler(self._data.i_train_dict,
                                     self._data.side_information_data.visual_feat_map_feature_path,
                                     self._data.visual_feat_map_features_shape,
                                     self._epochs)

        self._next_batch = self._sampler.pipeline(self._data.transactions, self._batch_size)

        self._model = ACF_model(self._factors,
                                self._layers_component,
                                self._layers_item,
                                self._learning_rate,
                                self._l_w,
                                self._data.visual_feat_map_features_shape,
                                self._num_users,
                                self._num_items,
                                self._seed)
        # only for evaluation purposes
        self._next_eval_batch = self._sampler.pipeline_eval()

    @property
    def name(self):
        return "ACF" \
               + f"_{self.get_base_params_shortcut()}" \
               + f"_{self.get_params_shortcut()}"

    def train(self):
        if self._restore:
            return self.restore_weights()

        for it in self.iterate(self._epochs):
            loss = 0
            steps = 0
            with tqdm(total=int(self._num_users // self._batch_size), disable=not self._verbose) as t:
                for batch in self._sampler.step(self._num_users, self._batch_size):
                    steps += 1
                    loss += self._model.train_step(batch)
                    t.set_postfix({'loss': f'{loss.numpy()/steps:.5f}'})
                    t.update()

            self.evaluate(it, loss.numpy()/(it + 1))
