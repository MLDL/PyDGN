import torch
from config.utils import s2c
from sklearn.metrics import r2_score, roc_auc_score, average_precision_score, accuracy_score

from datasets.splitter import to_lower_triangular
from training.core.event.handler import EventHandler


class Score(EventHandler):
    """
    Score is the main event handler for score metrics. Other scores can easily subclass by implementing the __call__
    method, though sometimes more complex implementations are required.
    """
    __name__ = 'score'

    def __init__(self):
        super().__init__()
        assert hasattr(self, '__name__')
        self.batch_scores = None
        self.num_targets = None

    def get_main_score_name(self):
        """
        Used by the training engine to retrieve the main score (assuming multiple scores are used)
        :return: the main score name
        """
        return self.__name__

    def _score_fun(self, targets, *outputs):
        raise NotImplementedError('To be implemented by a subclass')

    def on_training_epoch_start(self, state):
        """
        Initializes the array with batches of score values
        :param state: the shared State object
        """
        self.batch_scores = []
        self.num_targets = 0

    def on_training_batch_end(self, state):
        """
        Updates the array of batch score
        :param state: the shared State object
        """
        self.batch_scores.append(state.batch_score[self.__name__].item() * state.batch_num_targets)
        self.num_targets += state.batch_num_targets

    def on_training_epoch_end(self, state):
        """
        Computes a score value for the entire epoch
        :param state: the shared State object
        """
        state.update(epoch_score={self.__name__: torch.tensor(self.batch_scores).sum()/self.num_targets})
        self.batch_scores = None
        self.num_targets = None

    def on_eval_epoch_start(self, state):
        """
        Initializes the array with batches of score values
        :param state: the shared State object
        """
        self.batch_scores = []
        self.num_targets = 0

    def on_eval_epoch_end(self, state):
        """
        Computes a score value for the entire epoch
        :param state: the shared State object
        """
        state.update(epoch_score={self.__name__: torch.tensor(self.batch_scores).sum()/self.num_targets})
        self.batch_scores = None
        self.num_targets = None

    def on_eval_batch_end(self, state):
        """
        Updates the array of batch score
        :param state: the shared State object
        """
        self.batch_scores.append(state.batch_score[self.__name__].item() * state.batch_num_targets)
        self.num_targets += state.batch_num_targets

    def on_compute_metrics(self, state):
        """
        Computes the score
        :param state: the shared State object
        """
        outputs, targets = state.batch_outputs, state.batch_targets
        score = self(targets, *outputs, batch_loss_extra=getattr(state, 'batch_loss_extra', None))
        # Score is a dictionary with key-value pairs
        # we need to detach each score from the graph
        score = {k: v.detach() for k, v in score.items()}
        state.update(batch_score=score)

    def __call__(self, targets, *outputs, batch_loss_extra):
        """
        :param targets:
        :param outputs: a tuple of outputs returned by a model
        :param batch_loss_extra: optional loss extra vars to save compute time
        :return: dictionary with {score_name: score value}
        """
        score = self._score_fun(targets, *outputs, batch_loss_extra=batch_loss_extra)
        return {self.__name__: score}


class MultiScore(Score):
    __name__ = 'score'

    def _istantiate_scorer(self, scorer):
        if isinstance(scorer, dict):
            args = scorer["args"]
            return s2c(scorer['class_name'])(*args)
        else:
            return s2c(scorer)()

    def __init__(self, main_scorer, **extra_scorers):
        super().__init__()
        self.scorers = [self._istantiate_scorer(main_scorer)] + [self._istantiate_scorer(score) for score in extra_scorers.values()]

    def get_main_score_name(self):
        """
        Used by the training engine to retrieve the main score (assuming multiple scores are used)
        :return: the main score name
        """
        return self.scorers[0].get_main_score_name()

    def on_training_epoch_start(self, state):
        self.batch_scores = {s.__name__: [] for s in self.scorers}
        self.num_targets = 0

    def on_training_batch_end(self, state):
        for k,v in state.batch_score.items():
            self.batch_scores[k].append(v.item() * state.batch_num_targets)
        self.num_targets += state.batch_num_targets

    def on_training_epoch_end(self, state):
        state.update(epoch_score={s.__name__: torch.tensor(self.batch_scores[s.__name__]).sum()/self.num_targets
                                  for s in self.scorers})
        self.batch_scores = None
        self.num_targets = None

    def on_eval_epoch_start(self, state):
        self.batch_scores = {s.__name__: [] for s in self.scorers}
        self.num_targets = 0

    def on_eval_epoch_end(self, state):
        state.update(epoch_score={s.__name__: torch.tensor(self.batch_scores[s.__name__]).sum() / self.num_targets
                                  for s in self.scorers})
        self.batch_scores = None
        self.num_targets = None

    def on_eval_batch_end(self, state):
        for k,v in state.batch_score.items():
            self.batch_scores[k].append(v.item() * state.batch_num_targets)
        self.num_targets += state.batch_num_targets

    def __call__(self, targets, *outputs, batch_loss_extra):
        res = {}
        for scorer in self.scorers:
            # each scorer __call__ method returns a dict
            res.update(scorer(targets, *outputs, batch_loss_extra=batch_loss_extra))
        return res


class RSquareScore(Score):
    __name__ ='R2 Determination Coefficient'

    def __init__(self):
        super().__init__()
        self.y = None
        self.pred = None

    def on_training_epoch_start(self, state):
        super().on_training_epoch_start(state)
        self.y = None
        self.pred = None

    def on_training_epoch_end(self, state):
        state.update(epoch_score={self.__name__: r2_score(self.y.detach().cpu().numpy(), self.pred.detach().cpu().numpy())})
        self.batch_scores = None
        self.num_targets = None
        self.y = None
        self.pred = None

    def on_eval_epoch_start(self, state):
        super().on_eval_epoch_start(state)
        self.y = None
        self.pred = None

    def on_eval_epoch_end(self, state):
        state.update(epoch_score={self.__name__: r2_score(self.y.detach().cpu().numpy(), self.pred.detach().cpu().numpy())})
        self.batch_scores = None
        self.num_targets = None
        self.y = None
        self.pred = None

    def _score_fun(self, targets, *outputs, batch_loss_extra):
        self.y = targets if self.y is None else torch.cat((self.y, targets), dim=0)
        self.pred = outputs[0] if self.pred is None else torch.cat((self.pred, outputs[0]), dim=0)

        # Minibatch R2 score (needed when used with MultiScore, but behaves differently)
        return torch.tensor([r2_score(targets.detach().cpu().numpy(), outputs[0].detach().cpu().numpy())])


class BinaryAccuracyScore(Score):
    __name__ ='Binary Accuracy'

    def __init__(self):
        super().__init__()

    def _get_correct(self, output):
        return output > 0.5

    def _score_fun(self, targets, *outputs, batch_loss_extra):
        pred = outputs[0]

        if len(pred.shape) > 1:
            assert len(pred.shape) ==2 and pred.shape[1] == 1
            pred = pred.squeeze()

        correct = self._get_correct(pred)
        return 100. * (correct == targets).sum().float() / targets.size(0)


class Toy1Score(BinaryAccuracyScore):
    __name__ ='toy 1 accuracy'

    def __init__(self):
        super().__init__()

    def _get_correct(self, output):
        return torch.argmax(output, dim=1)

    def _score_fun(self, targets, *outputs, batch_loss_extra):
        return torch.tensor(75)


class MulticlassAccuracyScore(BinaryAccuracyScore):
    __name__ ='Multiclass Accuracy'

    def __init__(self):
        super().__init__()

    def _get_correct(self, output):
        return torch.argmax(output, dim=1)

    def _score_fun(self, targets, *outputs, batch_loss_extra):
        pred = outputs[0]
        correct = self._get_correct(pred)
        return 100. * (correct == targets).sum().float() / targets.size(0)


class DirichletPriorScore(Score):
    __name__ ='Dirichlet Prior'

    def __init__(self):
        super().__init__()

    def _score_fun(self, targets, *outputs, batch_loss_extra):
        return outputs[4]


class LikelihoodScore(Score):
    __name__ ='True Log Likelihood'

    def __init__(self):
        super().__init__()

    def _score_fun(self, targets, *outputs, batch_loss_extra):
        return outputs[3]
