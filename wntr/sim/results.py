import copy
import datetime
import enum

import pandas as pd

import numpy as np
import copy
import numpy as np
from wntr.epanet.util import FlowUnits, MassUnits, HydParam, QualParam
from wntr.epanet.util import from_si
from wntr.network.elements import Pipe, Pump, Valve, PRValve, PSValve, PBValve, FCValve

class ResultsStatus(enum.IntEnum):
    converged = 1
    error = 0


class SimulationResults(object):
    """
    Water network simulation results class.

    A small number of mathematical and statistical functions are also provided.
    These functions are applied to all dataframes within the results object (or
    between two results objects) by name, elementwise.

    Assuming ``A`` and ``B`` are both results objects that have the same time
    indices for the results and which describe the same water network physical
    model (i.e., have the same nodes and links), then the following functions 
    are defined:

    ==================  ===========================================================
    Example function    Description
    ------------------  -----------------------------------------------------------
    ``C = A + B``       Add the values from A and B for each property
    ``C = A - B``       Subtract the property values in B from A
    ``C = A / B``       Divide the property values in A by the values in B
    ``C = A / n``       Divide the property values in A by n [int];
                        note that this only makes sense if calculating an average
    ``C = A ** p``      Raise the property values in A to the p-th power;
                        note the syntax ``C = pow(A, p, mod)`` can also be used
    ``C = abs(A)``      Take the absolute value of the property values in A
    ``C = -A``          Take the negative of all property values in A
    ``C = +A``          Take the positive of all property values in A
    ==================  ===========================================================

    As an example, to calculate the relative difference between the results of two
    simulations, one could do: ``rel_dif = abs(A - B) / A`` (warning - this will operate
    on link statuses as well, which may result in meaningless results for that 
    parameter).

    """

    def __init__(self):

        # Simulation time series
        self.timestamp = str(datetime.datetime.now())
        self.network_name = None
        self.sim_time = 0
        self.link = None
        self.node = None

    def __add__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "{}[{}] + {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        for key in self.link.keys():
            if key in other.link:
                new.link[key] = self.link[key] + other.link[key]
        for key in self.node.keys():
            if key in other.node:
                new.node[key] = self.node[key] + other.node[key]
        return new

    def __sub__(self, other):
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "{}[{}] - {}[{}]".format(
            self.network_name, self.timestamp, other.network_name, other.timestamp
        )
        for key in self.link.keys():
            if key in other.link:
                new.link[key] = self.link[key] - other.link[key]
        for key in self.node.keys():
            if key in other.node:
                new.node[key] = self.node[key] - other.node[key]
        return new

    def __abs__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "|{}[{}]|".format(
            self.network_name, self.timestamp
        )
        for key in self.link.keys():
            new.link[key] = abs(self.link[key])
        for key in self.node.keys():
            new.node[key] = abs(self.node[key])
        return new

    def __neg__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "-{}[{}]".format(
            self.network_name, self.timestamp
        )
        for key in self.link.keys():
            new.link[key] = -self.link[key]
        for key in self.node.keys():
            new.node[key] = -self.node[key]
        return new

    def __pos__(self):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "+{}[{}]".format(
            self.network_name, self.timestamp
        )
        for key in self.link.keys():
            new.link[key] = +self.link[key]
        for key in self.node.keys():
            new.node[key] = +self.node[key]
        return new

    def __truediv__(self, other):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        if isinstance(other, SimulationResults):
            new.network_name = "{}[{}] / {}[{}]".format(
                self.network_name, self.timestamp, other.network_name, other.timestamp
            )
            for key in self.link.keys():
                if key in other.link:
                    new.link[key] = self.link[key] / other.link[key]
            for key in self.node.keys():
                if key in other.node:
                    new.node[key] = self.node[key] / other.node[key]
            return new
        elif isinstance(other, int):
            new.network_name = "{}[{}] / {}".format(
                self.network_name, self.timestamp, other
            )
            for key in self.link.keys():
                new.link[key] = self.link[key] / other
            for key in self.node.keys():
                new.node[key] = self.node[key] / other
            return new
        else:
            raise ValueError(
                "operating on a results object requires divisor be a SimulationResults or a float"
            )
        

    def __pow__(self, exp, mod=None):
        new = SimulationResults()
        new.link = dict()
        new.node = dict()
        new.network_name = "{}[{}] ** {}".format(
            self.network_name, self.timestamp, exp
        )
        for key in self.link.keys():
            new.link[key] = pow(self.link[key], exp, mod)
        for key in self.node.keys():
            new.node[key] = pow(self.node[key], exp, mod)
        return new

    def _adjust_time(self, ts: int):
        """
        Adjust the time index for the results object by `ts`.

        Parameters
        ----------
        ts : int
            The number of seconds by which to adjust the result dataframe index
        """
        ts = int(ts)
        for key in self.link.keys():
            self.link[key].index += ts
        for key in self.node.keys():
            self.node[key].index += ts

    def append_results_from(self, other):
        """
        Combine two results objects into a single, new result object.
        If the times overlap, then the results from the `other` object will take precedence 
        over the values in the calling object. I.e., given ``A.append_results_from(B)``, 
        where ``A`` and ``B``
        are both `SimluationResults`, any results from ``A`` that relate to times equal to or
        greater than the starting time of results in ``B`` will be dropped.

        .. warning::
        
            This operations will be performed "in-place" and will change ``A``


        Parameters
        ----------
        other : SimulationResults
            Results objects from a different, and subsequent, simulation.

        Raises
        ------
        ValueError
            if `other` is the wrong type
        
        """
        if not isinstance(other, SimulationResults):
            raise ValueError(
                "operating on a results object requires both be SimulationResults"
            )
        start_time = other.node['head'].index.values[0]
        keep = self.node['head'].index.values < start_time
        for key in self.link.keys():
            if key in other.link:
                t2 = self.link[key].loc[keep].append(other.link[key])
                self.link[key] = t2
            else:
                temp = other.link['flowrate'] * pd.nan
                t2 = self.link[key].loc[keep].append(temp)
                self.link[key] = t2
        for key in other.link.keys():
            if key not in self.link.keys():
                temp = self.link['flowrate'] * pd.nan
                t2 = temp.loc[keep].append(other.link[key])
                self.link[key] = t2
        for key in self.node.keys():
            if key in other.node:
                t2 = self.node[key].loc[keep].append(other.node[key])
                self.node[key] = t2
            else:
                temp = other.node['head'] * pd.nan
                t2 = self.node[key].loc[keep].append(temp)
                self.node[key] = t2
        for key in other.node.keys():
            if key not in self.node.keys():
                temp = self.node['head'] * pd.nan
                t2 = temp.loc[keep].append(other.node[key])
                self.node[key] = t2

    
