import unittest
import sys
# HACK until resilience is a proper module
# __file__ fails if script is called in different ways on Windows
# __file__ fails if someone does os.chdir() before
# sys.argv[0] also fails because it doesn't not always contains the path
import os, inspect
resilienceMainDir = os.path.abspath( 
    os.path.join( os.path.dirname( os.path.abspath( inspect.getfile( 
        inspect.currentframe() ) ) ), '..', '..' ))
#sys.path.append('../../')

import copy
import numpy as np
from scipy.optimize import fsolve

class TestNetworkCreation(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import epanetlib as en
        self.en = en

        inp_file = 'networks_for_testing/Net6_mod.inp'
        self.wn = self.en.network.WaterNetworkModel()
        parser = self.en.network.ParseWaterNetwork()
        parser.read_inp_file(self.wn, inp_file)

    @classmethod
    def tearDownClasss(self):
        sys.path.remove(resilienceMainDir)

    def test_num_junctions(self):
        self.assertEqual(self.wn._num_junctions, 3323)

    def test_num_reservoirs(self):
        self.assertEqual(self.wn._num_reservoirs, 1)

    def test_num_tanks(self):
        self.assertEqual(self.wn._num_tanks, 34)

    def test_num_pipes(self):
        self.assertEqual(self.wn._num_pipes, 3829)

    def test_num_pumps(self):
        self.assertEqual(self.wn._num_pumps, 61)

    def test_num_valves(self):
        self.assertEqual(self.wn._num_valves, 2)

    def test_junction_attr(self):
        j = self.wn.get_node('JUNCTION-18')
        self.assertAlmostEqual(j.base_demand, 48.56/60.0*0.003785411784)
        self.assertEqual(j.demand_pattern_name, 'PATTERN-2')
        self.assertAlmostEqual(j.elevation, 80.0*0.3048)

    def test_reservoir_attr(self):
        j = self.wn.get_node('RESERVOIR-3323')
        self.assertAlmostEqual(j.base_head, 27.45*0.3048)
        self.assertEqual(j.head_pattern_name, None)

class TestNetworkMethods(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        sys.path.append(resilienceMainDir)
        import epanetlib as en
        self.en = en

    @classmethod
    def tearDownClasss(self):
        sys.path.remove(resilienceMainDir)

    def test_add_junction(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_junction('j1', 150, 'pattern1', 15)
        j = wn.get_node('j1')
        self.assertEqual(j._name, 'j1')
        self.assertEqual(j.base_demand, 150.0)
        self.assertEqual(j.demand_pattern_name, 'pattern1')
        self.assertEqual(j.elevation, 15.0)
        self.assertEqual(wn._graph.nodes(),['j1'])
        self.assertEqual(type(j.base_demand), float)
        self.assertEqual(type(j.elevation), float)

    def test_add_tank(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_tank('t1', 15, 75, 0, 100, 10, 0)
        n = wn.get_node('t1')
        self.assertEqual(n._name, 't1')
        self.assertEqual(n.elevation, 15.0)
        self.assertEqual(n.init_level, 75.0)
        self.assertEqual(n.min_level, 0.0)
        self.assertEqual(n.max_level, 100.0)
        self.assertEqual(n.diameter, 10.0)
        self.assertEqual(n.min_vol, 0.0)
        self.assertEqual(wn._graph.nodes(),['t1'])
        self.assertEqual(type(n.elevation), float)
        self.assertEqual(type(n.init_level), float)
        self.assertEqual(type(n.min_level), float)
        self.assertEqual(type(n.max_level), float)
        self.assertEqual(type(n.diameter), float)
        self.assertEqual(type(n.min_vol), float)

    def test_add_reservoir(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_reservoir('r1', 30, 'pattern1')
        n = wn.get_node('r1')
        self.assertEqual(n._name, 'r1')
        self.assertEqual(n.base_head, 30.0)
        self.assertEqual(n.head_pattern_name, 'pattern1')
        self.assertEqual(wn._graph.nodes(),['r1'])
        self.assertEqual(type(n.base_head), float)

    def test_add_pipe(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pipe('p1', 'j1', 'j2', 1000, 1, 100, 0, 'Open')
        l = wn.get_link('p1')
        self.assertEqual(l._link_name, 'p1')
        self.assertEqual(l.start_node(), 'j1')
        self.assertEqual(l.end_node(), 'j2')
        self.assertEqual(l.get_base_status(), 'OPEN')
        self.assertEqual(l.length, 1000.0)
        self.assertEqual(l.diameter, 1.0)
        self.assertEqual(l.roughness, 100.0)
        self.assertEqual(l.minor_loss, 0.0)
        self.assertEqual(wn._graph.edges(), [('j1','j2')])
        self.assertEqual(type(l.length), float)
        self.assertEqual(type(l.diameter), float)
        self.assertEqual(type(l.roughness), float)
        self.assertEqual(type(l.minor_loss), float)

    def test_add_pipe_with_cv(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pipe('p1', 'j1', 'j2', 1000, 1, 100, 0, 'cv')
        self.assertEqual(wn._check_valves, ['p1'])

    def test_remove_pipe(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_junction('j3')
        wn.add_pipe('p2','j1','j3')
        wn.add_pipe('p1','j1','j2', status = 'cv')
        wn.remove_pipe('p1')
        link_list = [link_name for link_name, link in wn.links()]
        self.assertEqual(link_list, ['p2'])
        self.assertEqual(wn._check_valves,[])
        self.assertEqual(wn._num_pipes, 1)
        self.assertEqual(wn._graph.edges(), [('j1','j3')])

    def test_1_pt_head_curve(self):
        q2 = 10.0
        h2 = 20.0
        wn = self.en.network.WaterNetworkModel()
        wn.add_curve('curve1','HEAD',[(q2, h2)])
        curve = wn.get_curve('curve1')
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pump('p1', 'j1', 'j2', 'HEAD', curve)
        link = wn.get_link('p1')
        a,b,c = link.get_head_curve_coefficients()
        q1 = 0.0
        h1 = 4.0/3.0*h2
        q3 = 2.0*q2
        h3 = 0.0

        def curve_fun(x):
            f=[1.0,1.0,1.0]
            f[0] = h1 - x[0] + x[1]*q1**x[2]
            f[1] = h2 - x[0] + x[1]*q2**x[2]
            f[2] = h3 - x[0] + x[1]*q3**x[2]
            return f

        X = [a,b,c]
        Y = curve_fun(X)

        self.assertAlmostEqual(Y[0],0.0)
        self.assertAlmostEqual(Y[1],0.0)
        self.assertAlmostEqual(Y[2],0.0)

    def test_3_pt_head_curve(self):
        q1 = 0.0
        h1 = 35.0
        q2 = 10.0
        h2 = 20.0
        q3 = 18.0
        h3 = 2.0
        wn = self.en.network.WaterNetworkModel()
        wn.add_curve('curve1','HEAD',[(q1, h1),(q2,h2),(q3,h3)])
        curve = wn.get_curve('curve1')
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_pump('p1', 'j1', 'j2', 'HEAD', curve)
        link = wn.get_link('p1')
        a,b,c = link.get_head_curve_coefficients()

        def curve_fun(x):
            f=[1.0,1.0,1.0]
            f[0] = h1 - x[0] + x[1]*q1**x[2]
            f[1] = h2 - x[0] + x[1]*q2**x[2]
            f[2] = h3 - x[0] + x[1]*q3**x[2]
            return f

        X = [a,b,c]
        Y = curve_fun(X)

        self.assertAlmostEqual(Y[0],0.0)
        self.assertAlmostEqual(Y[1],0.0)
        self.assertAlmostEqual(Y[2],0.0)

    def test_get_links_for_node(self):
        wn = self.en.network.WaterNetworkModel()
        wn.add_junction('j1')
        wn.add_junction('j2')
        wn.add_junction('j3')
        wn.add_junction('j4')
        wn.add_junction('j5')
        wn.add_pipe('p1','j1','j2')
        wn.add_pipe('p2','j1','j4')
        wn.add_pipe('p3','j1','j5')
        wn.add_pipe('p4','j3','j2')
        l1 = wn.get_links_for_node('j1')
        l2 = wn.get_links_for_node('j2')
        l3 = wn.get_links_for_node('j3')
        l4 = wn.get_links_for_node('j4')
        l5 = wn.get_links_for_node('j5')
        l1.sort()
        l2.sort()
        l3.sort()
        l4.sort()
        l5.sort()
        self.assertEqual(l1,['p1','p2','p3'])
        self.assertEqual(l2,['p1','p4'])
        self.assertEqual(l3,['p4'])
        self.assertEqual(l4,['p2'])
        self.assertEqual(l5,['p3'])

if __name__ == '__main__':
    unittest.main()
