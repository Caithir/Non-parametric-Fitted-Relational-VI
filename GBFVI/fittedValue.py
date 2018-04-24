import sys
from collections import defaultdict
from box_world import Logistics
from wumpus import Wumpus
from blocks import Blocks_world
from blackjack import Game
from chain import Chain
from net_admin import Admin
# from pong import Pong 
# from tetris import Tetris
from time import clock
from GradientBoosting import GradientBoosting
from copy import deepcopy


def main():

    '''
    Can specify options here or from the command line but command line options take presidence
    Command line arguments follow the form: -<variable_name> <value>
    example to run wumpus world with 100 iterations and a batchsize of 20: -simulator wumpus -number_of_iterations 100 -batch_size 20
'''
    options = {"simulator": "50chain",
               "batch_size": 10,
               "number_of_iterations": 100}
    if len(sys.argv) > 1:
        getopts(sys.argv, options) 

    FittedValueIteration(**options).GBAD()

class FittedValueIteration(object):
    def __init__(self,transfer=0,simulator="logistics",batch_size=1,number_of_iterations=10,loss="LS",trees=10):
        self.batch_size = int(batch_size)
        self.loss = loss
        self.trees = int(trees)
        self.number_of_iterations = int(number_of_iterations)
        self.model = self.getModel(regression = True,treeDepth=2,sampling_rate=0.7)
        self.simulatorName = simulator
        self.simulator = self.getSimulator(self.simulatorName)
        self.cumulativeTrajectories = []
        self.model.learn(self.simulator.get_state_facts(),["value(s{}) 0.0".format(str(self.simulator))], self.simulator.bk)

    def GBAD(self, discountFactor = .9):
        for i in range(self.number_of_iterations):
            values = defaultdict(int)
            facts, examples, bk =[], [], self.simulator.bk
            X = self.sampleTrajectories(self.batch_size)
            self.cumulativeTrajectories.append(X)

            # state representations not actual states
            for currentState, reward, nextState in X:
                nextStateValue = self.getStateValueFromTree(currentState, nextState)
                values[currentState[0]] = reward + discountFactor*nextStateValue
                facts.extend(currentState[1])
                examples.append("value(s{}) {}".format(currentState[0],values[currentState[0]]))
            self.RFGB(values, facts, examples, bk, i)

    def RFGB(self, values, facts, examples, bk, i):
        self.model.learn(facts,examples,bk)

        # averageBellmanError  = self.averageBellmanError()
        with open("./outputs/{}_DRs.txt".format(self.simulatorName),"a") as f:
            f.write("iteration: {} Discounted reward: {} \n".format(i,averageBellmanError))

    def averageBellmanError(self):
        bellmanErrors = []
        _ = ''
        trajectories = self.sampleTrajectories(self.batch_size)
        for currentState, reward, nextState in trajectories:
            if currentState == nextState:
                continue
            currentStateValue = self.getStateValueFromTree(_, currentState)
            nextStateValue = self.getStateValueFromTree(_, nextState)

            bellmanError = abs(currentStateValue - reward - nextStateValue)
            bellmanErrors.append(bellmanError)
        return float(sum(bellmanErrors)) / max(len(bellmanErrors), 1)

        

    def getStateValueFromTree(self,currentState, nextState):
        # The only way for a state to transistion to itself is if it is a goal state and should not grab value from tree
        if currentState == nextState:
            return 0 
        facts = nextState[1]
        example_predicate = "value(s{})".format(nextState[0])
        examples = [example_predicate+" 0.0"]
        self.model.infer(facts,examples)
        return self.model.testExamples["value"][example_predicate]

    
    def sampleTrajectories(self, number_of_trajectories):
        """
        Returns a list of tuples representing (state, reward, next_state)
            state and next_state are themselves tuples containing the state representation and the facts of the state
        """
        trajectories = []
        timeout = {"logistics":0.5, "pong":1000, "tetris":10, "wumpus":1,
            "blocks":1, "blackjack":1, "50chain":1, "net_id":1}
        for i in range(number_of_trajectories):
            state = self.getSimulator(self.simulatorName)
            with open("./outputs/{}_FVI_out.txt".format(self.simulatorName),"a") as f:
                f.write("{}\nstart state: {}: facts {} \n".format('*'*80, state, str(state.get_state_facts())))
                start = clock()
                trajectory = []
                while not state.goal():
                    f.write("{}\n".format('='*80))
                    #exucute_random_action modifies the state so relevant information needs to be extracted first
                    reward = state.getReward()
                    stateRep = str(state)
                    stateFacts = state.get_state_facts()
                    
                    nextState, action, _ = state.execute_random_action()
                    trajectory.append(( (stateRep, stateFacts), reward, (str(nextState), nextState.get_state_facts()) ))
                    
                    # Does nothing since state and nextState are the same
                    # state = nextState 
                    f.write("{} : {}\n".format(stateRep, stateFacts))
                trajectory.append(((str(state), state.get_state_facts()), state.getReward(), (str(state), state.get_state_facts())))
                end = clock()
                time_elapsed = abs(end-start)
                if time_elapsed > timeout[self.simulatorName]:
                    print("Time out")
                    continue
                trajectories.extend(trajectory)
        return trajectories
    
    #do this over the trajs at once? does it matter that much?
    def discountedSumOfRewards(self, trajectory, discountFactor = .9):
        discountedReward = 0
        iteration = 0
        for _, reward, _ in trajectory:
            discountedReward+= pow(discountFactor, iteration) * reward

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