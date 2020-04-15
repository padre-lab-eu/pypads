from pypads import logger
from pypads.base import PyPads
tracker = PyPads()

from sklearn import datasets
from sklearn.metrics.classification import f1_score
from sklearn.tree import DecisionTreeClassifier

# load the iris datasets
dataset = datasets.load_iris()

# fit a model to the data
model = DecisionTreeClassifier()
model.fit(dataset.data, dataset.target)
# make predictions
expected = dataset.target
predicted = model.predict(dataset.data)
# summarize the fit of the model
logger.error("Score: " + str(f1_score(expected, predicted, average="macro")))

tracker.api.end_run()
