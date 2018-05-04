import sys
from collections import defaultdict
from box_world import Logistics
from wumpus import Wumpus
from blocks import Blocks_world
from blackjack import Game
from chain import Chain
from net_admin import Admin
# from pong import Pong 
from tetris import Tetris
from time import clock
from GradientBoosting import GradientBoosting
from copy import deepcopy
import random
from sklearn.utils import shuffle


def main():

    '''
    Can specify options here or from the command line but command line options take presidence
    Command line arguments follow the form: -<variable_name> <value>
    example to run wumpus world with 100 iterations and a batchsize of 20: -simulator wumpus -number_of_iterations 100 -batch_size 20
'''
    options = {"simulator": "tetris",
               "batch_size": 10,
               "number_of_iterations": 20}
    if len(sys.argv) > 1:
        getopts(sys.argv, options) 

    QLearning(**options).GBAD()

class QLearning(object):
    def __init__(self,transfer=0,simulator="logistics",batch_size=10,number_of_iterations=10,loss="LS",trees=10):
        self.batch_size = int(batch_size)
        self.loss = loss
        self.trees = int(trees)
        self.number_of_iterations = int(number_of_iterations)
        self.simulatorName = simulator
        self.simulator = self.getSimulator(self.simulatorName)
        self.modelsUninitialized = True
        self.stateTransitions = {}
        self.actionFunctions = {}
        for action in self.simulator.all_actions:
            self.actionFunctions[action] = self.getModel(regression = True,treeDepth=2,sampling_rate=0.7)


    def GBAD(self, discountFactor = .9):
        for i in range(self.number_of_iterations):
            Q = defaultdict(int)
            facts, examples, bk = defaultdict(list), defaultdict(list), self.simulator.bk
            X = self.sampleTrajectories(self.batch_size)
           
            # state representations not actual states
            for currentState, action, reward, nextState in X:
                nextStateValue, _ = self.qValueFromModel(nextState, prevState= currentState)
                Q[(currentState[0], action)] = reward+discountFactor*nextStateValue
    
                facts[action].extend(currentState[1])
                examples[action].append("value(s{}) {}".format(currentState[0], Q[(currentState[0], action)]))

            #Goal states transition to themselves but thier q value needs to be defined over an action from the simulator
            for action in self.simulator.all_actions:
                facts[action].extend(facts[""])
                examples[action].extend(examples[""])
            self.RFGB( facts, examples, bk)
            self.averageDiscountedSumOfReturns()


    def averageDiscountedSumOfReturns(self, number_of_runs = 10):
        with open("./outputs/{}_DRs.txt".format(self.simulatorName),"a") as f:
            
            discountedSums=[]
            for i in range(number_of_runs):
                rewards = self.sampleTrajectoryFromPolicy()
                discountedSum = self.discountedSumOfRewards(rewards)
                if discountedSum != None:
                    discountedSums.append(discountedSum) 
            averageDiscountedSum = float(sum(discountedSums)) / max(len(discountedSums), 1)
            f.write("Average Discounted reward: {} \n".format( averageDiscountedSum))
            return averageDiscountedSum
            
   
    def sampleTrajectoryFromPolicy(self):
        """
        Returns a list of reward for a given policy
        """
        timeout = {"logistics":0.5, "pong":1000, "tetris":9999999, "wumpus":1,
            "blocks":1, "blackjack":1, "50chain":1, "net_id":1}
    
        state = self.getSimulator(self.simulatorName)
        start = clock()
        rewards = []
        while not state.goal():
            #exucute_random_action modifies the state so relevant information needs to be extracted first
            _, action = self.qValueFromModel((str(state), state.get_state_facts()), actions=state.get_legal_actions())
            rewards.append(state.getReward())
            state.execute_action(action)
            end = clock()           
            time_elapsed = abs(end-start)
            if time_elapsed > timeout[self.simulatorName]:
                print("Time out")
                return []
        rewards.append(state.getReward())
        
        
        return rewards


    def getActionFromPolicy(self, Q, state):
        keysWithState = [item for item in Q if str(state) == item[0].split(":")[0]]
        vals = [(key[1], Q[key]) for key in keysWithState]
        vals = shuffle(vals)
        action = max(vals, key=lambda item:item[1])
        ties = [x for x in vals if x[1] == action[1]]
        return random.choice(ties)[0]


    def RFGB(self, facts, examples, bk):
        self.modelsUninitialized = False
        for action in self.simulator.all_actions:
            self.actionFunctions[action].learn(facts[action],examples[action],bk)


    def qValueFromModel(self, state, prevState=None, actions=None):
        if self.modelsUninitialized:
            return 0, ""
        if prevState:
            if state[0] == prevState[0]:
                return 0, ""    
        if not actions:
            actions = self.actionFunctions.keys()
        inferedValues = []
        for action in actions:
            model = self.actionFunctions[action]
            facts, examples= [], []
            facts.extend(state[1])
            example_predicate = "value(s{})".format(state[0])
            examples.append(example_predicate+ " 0.0")
            print "{}: ".format(action),
            model.infer(facts,examples)
            inferedValues.append((model.testExamples["value"][example_predicate], action))

        maxValue, maxAction = max(inferedValues, key=lambda item:item[0])
        return maxValue, maxAction


    def sampleTrajectories(self, number_of_trajectories):
        """
        Returns a list of tuples representing (state, reward, next_state)
            state and next_state are themselves tuples containing the state representation and the facts of the state
        """
        trajectories = []
        test = {}
        timeout = {"logistics":0.5, "pong":1000, "tetris":999999, "wumpus":1,
            "blocks":1, "blackjack":1, "50chain":1, "net_id":1}
        for i in range(number_of_trajectories):
                
            # with open("./outputs/{}_QL_out.txt".format(self.simulatorName),"a") as f:
            #     f.write("{}\nstart state: {}: facts {} \n".format('*'*80, state, str(state.get_state_facts())))
                state = self.getSimulator(self.simulatorName)
                start = clock()
                trajectory = []
                prevState = ""
                while not state.goal():
                    # f.write("{}\n".format('='*80))
                    #exucute_random_action modifies the state so relevant information needs to be extracted first
                    
                    reward = state.getReward()
                    stateRep = str(state)
                    stateFacts = state.get_state_facts()
                    prevState = stateRep
    
                    nextState, action, _ = state.execute_random_action()
                   
                    
                    newStateRep= stateRep 
                    
                    trajectory.append(( (newStateRep, stateFacts), action, reward, (str(nextState), nextState.get_state_facts()) ))
                #adding goal state to trajectory    
                trajectory.append(((str(state), state.get_state_facts()), '', state.getReward(), (str(state), state.get_state_facts())))
            
                end = clock()
                time_elapsed = abs(end-start)
                if time_elapsed > timeout[self.simulatorName]:
                    print("Time out")
                    continue
                trajectories.extend(trajectory)
        return trajectories
    
    def discountedSumOfRewards(self, rewards, discountFactor = .9):
        discountedReward = 0.0
        for iteration, reward in enumerate(rewards):
            discountedReward += pow(discountFactor, iteration) * reward
        return discountedReward

    def getModel(self,regression = True,treeDepth=2,sampling_rate=0.7):
        model = GradientBoosting(regression = True,treeDepth=2,trees=self.trees,sampling_rate=0.7,loss=self.loss)
        model.setTargets(["value"])
        return model  

    def getSimulator(self, simulator):
        if simulator == "logistics":
            return Logistics(start=True)
            
        elif simulator == "pong":
            return Pong(start=True)
            
        elif simulator == "tetris":
            return Tetris(start=True)
            
        elif simulator == "wumpus":
            return Wumpus(start=True)
           
        elif simulator == "blocks":
            return Blocks_world(start=True)
          
        elif simulator == "blackjack":
            return Game(start=True)
           
        elif simulator == "50chain":
            return Chain(start=True)
          
        elif simulator == "net_admin":
            return Admin(start=True)
        else:
            print('{} is not a supported simulation'.format(simulator))
            raise NameError()
          

def getopts(argv, opts):  
    while argv:  
        if argv[0][0] == '-':  
            opts[argv[0][1:]] = argv[1]  
        argv = argv[1:]  
    return opts

if __name__ == "__main__":
    main()