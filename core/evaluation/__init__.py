"""Evaluation framework — benchmarks, truth, replay, product verification."""
from .framework import EvaluationRunner, TaskResult, TaskCorpus, get_evaluation_runner
from .truth import ExperimentalTruthLayer, get_truth
from .replay import ReplayEngine, get_replay_engine
from .swebench import SWEBenchRunner, get_swe_runner
