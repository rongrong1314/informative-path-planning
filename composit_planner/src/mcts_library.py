# !/usr/bin/python

'''
This library allows access to the Monte Carlo Tree Search class used in the PLUMES framework.
A MCTS allows for performing many forward simulation of multiple-chained actions in order to 
select the single most promising action to take at some time t. We have presented a variation
of the MCTS by forward simulating within an incrementally updated GP belief world.

License: MIT
Maintainers: Genevieve Flaspohler and Victoria Preston
'''
# System Includes
from itertools import chain
import numpy as np
import scipy as sp
import math
import os
import time
import copy
import random

# Custom libraries
import GPy as GPy
from aq_library import *

# ROS Imports 
from geometry_msgs.msg import Pose

class Node(object):
    def __init__(self, pose, parent, name, action = None, dense_path = None, zvals = None):
        self.pose = pose
        self.name = name
        self.zvals = zvals
        self.reward = 0.0
        self.nqueries = 0
        
        # Parent will be none if the node is a root
        self.parent = parent
        self.children = None

        # Set belief or belief action node
        if action is None:
            self.node_type = 'B'
            self.action = None 
            self.dense_path = None

            # If the root node, depth is 0
            if parent is None:
                self.depth = 0
            else:
                self.depth = parent.depth + 1
        else:
            self.node_type = 'BA'
            self.action = action
            self.dense_path = dense_path
            self.depth = parent.depth

    def add_children(self, child_node):
        if self.children is None:
            self.children = []
        self.children.append(child_node)
    
    def print_self(self):
        print self.name

class DPWTree(object):
    def __init__(self, f_aqu, belief, pose, path_service, time, depth, c):
        self.path_service = path_service
        self.max_depth = depth
        self.param = param
        self.t = time
        self.f_rew = f_rew
        self.aquisition_function = f_aqu
        self.c = c

        self.root = Node(pose, parent = None, name = 'root', action = None, dense_path = None, zvals = None)  
        #self.build_action_children(self.root) 

    def get_best_child(self):
        return self.root.children[np.argmax([node.nqueries for node in self.root.children])]

    def backprop(self, leaf_node, reward):
        if leaf_node.parent is None:
            leaf_node.nqueries += 1
            leaf_node.reward += reward
            return
        else:
            leaf_node.nqueries += 1
            leaf_node.reward += reward
            self.backprop(leaf_node.parent, reward)
            return
    
    def get_next_leaf(self, belief):
        next_leaf, reward = self.leaf_helper(self.root, reward = 0.0,  belief = belief) 
        self.backprop(next_leaf, reward)

    def leaf_helper(self, current_node, reward, belief):
        if current_node.node_type == 'B':
            # Root belief node
            if current_node.depth == self.max_depth:
                return current_node, reward
            # Intermediate belief node
            else:
                if current_node.children is None:
                    self.build_action_children(current_node)

                # If no viable actions are avaliable
                if current_node.children is None:
                    return current_node, reward

                child = self.get_next_child(current_node)
                #print "Selecting next action child:", child.name

                # Recursive call
                return self.leaf_helper(child, reward, belief)

        # At random node, after selected action from a specific node
        elif current_node.node_type == 'BA':
            # Copy old belief
            #gp_new = copy.copy(current_node.belief) 
            #gp_new = current_node.belief

            # Sample a new set of observations and form a new belief
            #xobs = current_node.action
            #obs = np.array(current_node.action)
            #xobs = np.vstack([obs[:,0], obs[:,1]]).T
            r = self.predict_aqu(current_node.action, time = self.t)
            r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)

            if self.f_rew == 'mes' or self.f_rew == 'maxs-mes':
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)
            elif self.f_rew == 'exp_improve':
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)
            else:
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief)

            if current_node.children is not None:
                alpha = 3.0 / (10.0 * (self.max_depth - current_node.depth) - 3.0)
                nchild = len(current_node.children)
                #print "Current depth:", current_node.depth, "alpha:", alpha
                #print "First:", np.floor(nchild ** alpha)
                #print "Second:", np.floor((nchild - 1) ** alpha)
                if current_node.depth < self.max_depth - 1 and np.floor(nchild ** alpha) == np.floor((nchild - 1) ** alpha):
                    #print "Choosing from among current nodes"
                    #child = random.choice(current_node.children)
                    #print "number quieres:", nqueries
                    child = random.choice(current_node.children)
                    nqueries = [node.nqueries for node in current_node.children]
                    child = random.choice([node for node in current_node.children if node.nqueries == min(nqueries)])
                    belief.add_data(xobs, child.zvals)
                    #print "Selcted child:", child.nqueries
                    return self.leaf_helper(child, reward + r, belief)

            if belief.model is None:
                n_points, input_dim = xobs.shape
                zmean, zvar = np.zeros((n_points, )), np.eye(n_points) * belief.variance
                zobs = np.random.multivariate_normal(mean = zmean, cov = zvar)
                zobs = np.reshape(zobs, (n_points, 1))
            else:
                zobs = belief.posterior_samples(xobs, full_cov = False, size = 1)

            belief.add_data(xobs, zobs)
            pose_new = current_node.dense_path[-1]
            child = Node(pose = pose_new, 
                         parent = current_node, 
                         name = current_node.name + '_belief' + str(current_node.depth + 1), 
                         action = None, 
                         dense_path = None, 
                         zvals = zobs)
            #print "Adding next belief child:", child.name
            current_node.add_children(child)

            # Recursive call
            return self.leaf_helper(child, reward + r, belief)

    def get_next_child(self, current_node):
        vals = {}
        # e_d = 0.5 * (1.0 - (3.0/10.0*(self.max_depth - current_node.depth)))
        e_d = 0.5 * (1.0 - (3.0/(10.0*(self.max_depth - current_node.depth))))
        for i, child in enumerate(current_node.children):
            #print "Considering child:", child.name, "with queries:", child.nqueries
            if child.nqueries == 0:
                return child
            vals[child] = child.reward/float(child.nqueries) + self.c * np.sqrt((float(current_node.nqueries) ** e_d)/float(child.nqueries)) 
            #vals[child] = child.reward/float(child.nqueries) + self.c * np.sqrt(np.log(float(current_node.nqueries))/float(child.nqueries)) 
        # Return the max node, or a random node if the value is equal
        return random.choice([key for key in vals.keys() if vals[key] == max(vals.values())])
        
    def build_action_children(self, parent):
        actions, dense_paths = self.path_service.get_path_set(parent.pose)
        if len(actions) == 0:
            print "No actions!", 
            return
        
        #print "Creating children for:", parent.name
        for i, action in enumerate(actions.keys()):
            #print "Action:", i
            parent.add_children(Node(pose = parent.pose, 
                                    parent = parent, 
                                    name = parent.name + '_action' + str(i), 
                                    action = actions[action], 
                                    dense_path = dense_paths[action],
                                    zvals = None))

    def print_tree(self):
        counter = self.print_helper(self.root)
        print "# nodes in tree:", counter

    def print_helper(self, cur_node):
        if cur_node.children is None:
            #cur_node.print_self()
            #print cur_node.name
            return 1
        else:
            #cur_node.print_self()
            #print "\n"
            counter = 0
            for child in cur_node.children:
                counter += self.print_helper(child)
            return counter

''' Inherit class, that implements more standard MCTS, and assumes MLE observation to deal with continuous spaces '''
class MLETree(DPWTree):
    def __init__(self, f_aqu, belief, pose, path_service, time, depth, c):
        super(MLETree, self).__init__(f_aqu,  belief, pose, path_service, time, depth, c)

    # Max Reward-based node selection
    def get_best_child(self):
        return self.root.children[np.argmax([node.nqueries for node in self.root.children])]

    def random_rollouts(self, current_node, reward, belief):
        cur_depth = current_node.depth
        pose = current_node.pose
        while cur_depth <= self.max_depth:
            actions, dense_paths = self.path_service.get_path_set(pose)
            keys = actions.keys()
            # No viable trajectories from current location
            if len(actions) <= 1:
                return reward

            #select a random action
            a = np.random.randint(0, len(actions) - 1)
            obs = np.array(actions[keys[a]])
            xobs = np.vstack([obs[:,0], obs[:,1]]).T

            if self.f_rew == 'mes' or self.f_rew == 'maxs-mes':
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)
            elif self.f_rew == 'exp_improve':
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)
            else:
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief)

            # ''Simulate'' the maximum likelihood observation
            if belief.model is None:
                n_points, input_dim = xobs.shape
                zobs = np.zeros((n_points, ))
                zobs = np.reshape(zobs, (n_points, 1))
            else:
                zobs, _= belief.predict_value(xobs)

            belief.add_data(xobs, zobs)
            pose = dense_paths[keys[a]][-1]
            reward += r
            cur_depth += 1

        return reward

    def leaf_helper(self, current_node, reward, belief):
        if current_node.node_type == 'B':
            # belief node
            if current_node.depth == self.max_depth:
                # Return leaf node and reward
                return current_node, reward
            # Intermediate belief node
            else:
                if current_node.children is None:
                    self.build_action_children(current_node)

                # If no viable actions are avaliable
                if current_node.children is None:
                    return current_node, reward

                child, full_action_set  = self.get_next_child(current_node)

                if full_action_set:
                    # Recursive call
                    return self.leaf_helper(child, reward, belief)
                else:
                    # Do random rollouts
                    rollout_reward = self.random_rollouts(current_node, reward, belief) 
                    return child, rollout_reward

        # At random node, after selected action from a specific node
        elif current_node.node_type == 'BA':
            # Copy old belief
            #gp_new = copy.copy(current_node.belief) 
            #gp_new = current_node.belief

            # Sample a new set of observations and form a new belief
            obs = np.array(current_node.action)
            xobs = np.vstack([obs[:,0], obs[:,1]]).T

            if self.f_rew == 'mes' or self.f_rew == 'maxs-mes':
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)
            elif self.f_rew == 'exp_improve':
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief, param = self.param)
            else:
                r = self.aquisition_function(time = self.t, xvals = xobs, robot_model = belief)

            # ''Simulate'' the maximum likelihood observation
            if belief.model is None:
                n_points, input_dim = xobs.shape
                zobs = np.zeros((n_points, ))
                zobs = np.reshape(zobs, (n_points, 1))
            else:
                zobs, _= belief.predict_value(xobs)

            belief.add_data(xobs, zobs)
            pose_new = current_node.dense_path[-1]
            child = Node(pose = pose_new, 
                         parent = current_node, 
                         name = current_node.name + '_belief' + str(current_node.depth + 1), 
                         action = None, 
                         dense_path = None, 
                         zvals = zobs)
            #print "Adding next belief child:", child.name
            current_node.add_children(child)

            # Recursive call
            return self.leaf_helper(child, reward + r, belief)

    ''' Returns the next most promising child of a belief node, and a FLAG indicating if belief node is fully explored '''
    def get_next_child(self, current_node):
        vals = {}
        for i, child in enumerate(current_node.children):
            #print "Considering child:", child.name, "with queries:", child.nqueries
            if child.nqueries == 0:
                return child, False
            vals[child] = child.reward/float(child.nqueries) + self.c * np.sqrt(2.0*np.log(float(current_node.nqueries))/float(child.nqueries)) 
        # Return the max node, or a random node if the value is equal
        return random.choice([key for key in vals.keys() if vals[key] == max(vals.values())]), True
        

class cMCTS():
    '''Class that establishes a continuous MCTS for nonmyopic planning'''
    def __init__(self, belief, initial_pose, computation_budget, rollout_length, path_service, eval_value, time, tree_type = None):
        '''
        Initialize with constraints for the planning, including whether there is a budget or planning horizon
        Inputs:
            computation_budget (float) number of seconds to run the tree building procedure
            belief (GP model) current belief of the vehicle
            initial_pose (tuple of floats) location of the vehicle in world coordinates
            rollout_length (int) number of actions to rollout after selecting a child (tree depth)
            frontier_size (int) number of options for each action in the tree (tree breadth)
            path_service (string) how action sets should be developed
            aquisition_function (function) the criteria to make decisions
            f_rew (string) the name of the function used to make decisions
            T (float) time in the global world used for aquisition weighting
        '''
        # Status of the robot
        self.GP = belief
        self.pose = initial_pose # of type geometry_msgs/Pose
        self.path_service = path_service # function handle to service call
        self.eval_value = eval_value 

        # Parameterization for the search
        self.comp_budget = computation_budget
        self.rollout_len = rollout_length
        self.t = time

        # The tree
        self.tree = None
        self.tree_type = tree_type

        # The different constants for logarithmic vs polynomial exploration
        if self.f_rew == 'mean':
            if self.tree_type == 'mle_tree':
                self.c = 1000
            elif self.tree_type == 'dpw_tree':
                self.c = 5000
        elif self.f_rew == 'exp_improve':
            self.c = 200
        elif self.f_rew == 'mes':
            if self.tree_type == 'mle_tree':
                self.c = 1.0 / np.sqrt(2.0)
            elif self.tree_type == 'dpw_tree':
                # self.c = 1.0 / np.sqrt(2.0)
                self.c = 1.0
                # self.c = 5.0
        else:
            self.c = 1.0
        print "Setting c to :", self.c

    def choose_trajectory(self, t):
        #Main function loop which makes the tree and selects the best child
        #Output: path to take, cost of that path

        '''
        # randomly sample the world for entropy search function
        if self.f_rew == 'mes':
            self.max_val, self.max_locs, self.target  = sample_max_vals(self.GP, t = t)
            param = (self.max_val, self.max_locs, self.target)
        elif self.f_rew == 'exp_improve':
            param = [self.current_max]
        else:
            param = None
        '''

        # initialize tree
        if self.tree_type == 'dpw_tree':
            self.tree = DPWTree(self.eval_value, self.GP, self.pose, self.path_service, time = t, depth = self.rollout_len, c = self.c)
        elif self.tree_type == 'mle_tree':
            self.tree = MLETree(self.eval_value, self.GP, self.pose, self.path_service, time = t, depth = self.rollout_len, c = self.c)
        else:
            raise ValueError('Tree type must be one of either \'dpw_tree\' or \'mle_tree\'')

        time_start = time.time()            
        # While we still have time to compute, generate the tree
        i = 0
        while i < self.comp_budget: #time.time() - time_start < self.comp_budget:
            i += 1
            gp = copy.copy(self.GP)
            self.tree.get_next_leaf(gp)
        time_end = time.time()
        print "Rollouts completed in", str(time_end - time_start) +  "s"
        print "Number of rollouts:", i
        self.tree.print_tree()

        # TODO: update this code to return the right thing
        print [(node.nqueries, node.reward/node.nqueries) for node in self.tree.root.children]

        best_child = random.choice([node for node in self.tree.root.children if node.nqueries == max([n.nqueries for n in self.tree.root.children])])
        all_vals = {}
        for i, child in enumerate(self.tree.root.children):
            all_vals[i] = child.reward / float(child.nqueries)

        clear_paths = self.path_service(PathFromPoseRequest(self.pose))
        return best_child.action, best_child.dense_path, best_child.reward/float(best_child.nqueries), paths, all_vals, self.max_locs, self.max_val

        #Document the information
        #print "Number of rollouts:", i, "\t Size of tree:", len(self.tree)
        #logger.info("Number of rollouts: {} \t Size of tree: {}".format(i, len(self.tree)))
        #np.save('./figures/' + self.f_rew + '/tree_' + str(t) + '.npy', self.tree)
        #return self.tree[best_sequence][0], self.tree[best_sequence][1], best_val, paths, all_vals, self.max_locs, self.max_val

