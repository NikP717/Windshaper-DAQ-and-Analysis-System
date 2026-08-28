from models.WindAnalyser import WindAnalyser
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
from scipy.signal import correlate, correlation_lags, welch
from scipy.signal import welch, csd, detrend
from scipy import signal