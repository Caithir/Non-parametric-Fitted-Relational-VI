import random
class Game(object):
    '''class for new blackjack game'''

    bk = ["player_sum(+state,[low;high;very_high;blackjack])",
          "dealer_face_card(+state,[low;high;very_high])",
          "value(state)"]

    def __init__(self,start=False):
        '''class constructor'''
        if start:
            self.cards = self.makeCardDeck()
            self.initPSum = self.drawTwo(tot=True)
            self.initDCards = self.drawTwo()
            self.hand = [self.initPSum,self.initDCards[0]]
            self.all_actions = ["hit","stand"]
            self.stand = False

    def bust(self):
        '''checks if player has bust'''
        pSum = self.hand[0]
        if pSum > 21:
            return True
        return False
    
    def factored(self):
        '''returns factored state'''
        return [float(item) for item in list(self.hand)]
        
    def getReward(self):
        if self.bust():
            return -50
        if self.goal():
            pSum = self.hand[0]
            dSum = sum([float(item) for item in self.initDCards])
            if pSum > dSum:
                return 100
        return 0

    def goal(self):
        '''checks who won'''
        if self.bust():
            return True
        if self.stand:
            return True
        return False    

    def execute_action(self,action):
        '''performs action and returns state'''
        self.state_number += 1
        if self.goal():
            return self
        if action not in self.all_actions:
            return self
        if action == "hit":
            card = self.drawCard()
            pSum = self.hand[0]
            npSum = float(pSum)+float(card)
            self.hand[0] = npSum
            return self
        elif action == "stand":
            self.stand = True
            return self

    def get_state_facts(self):
        facts = []
        if int(self.hand[0]) in range(1,12):
            facts.append("player_sum(s{},low)".format(self.__str__()))
        elif int(self.hand[0]) in range(12,17):
            facts.append("player_sum(s{},high)".format(self.__str__()))
        elif int(self.hand[0]) in range(17,21):
            facts.append("player_sum(s{},very_high)".format(self.__str__()))
        elif int(self.hand[0]) == 21:
            facts.append("player_sum(s{},blackjack)".format(self.__str__()))
        if int(self.hand[1]) in range(1,5):
            facts.append("dealer_face_card(s{},low)".format(self.__str__()))
        elif int(self.hand[1]) in range(5,8):
            facts.append("dealer_face_card(s{},high)".format(self.__str__()))
        elif int(self.hand[1]) in range(8,11):
            facts.append("dealer_face_card(s{},very_high)".format(self.__str__()))
        return facts

    def sample(self,pdf):
        cdf = [(i, sum(p for j,p in pdf if j < i)) for i,_ in pdf]
        try:
            R = max(i for r in [random.random()] for i,c in cdf if c <= r)
        except ValueError:
            R = random.choice(self.all_actions)
        return R

    def get_legal_actions(self):
        return self.all_actions


    def execute_random_action(self):
        N = len(self.all_actions)
        random_actions = []
        action_potentials = []
        for i in range(N):
            random_action = random.choice(self.all_actions)
            random_actions.append(random_action)
            action_potentials.append(random.randint(1,9))
        action_probabilities = [potential/float(sum(action_potentials)) for potential in action_potentials]
        actions_not_executed = [action for action in self.all_actions if action != random_action]
        probability_distribution_function = zip(random_actions,action_probabilities)
        sampled_action = self.sample(probability_distribution_function)
        new_state = self.execute_action(sampled_action)
        return (new_state,sampled_action,actions_not_executed)

    def makeCardDeck(self):
        '''makes a deck of cards'''
        cards = []
        cards += [10 for i in range(16)]
        cards += [11 for i in range(4)]
        for i in range(1,10):
            cards += [i for j in range(4)]
        return cards

    def drawCard(self):
        '''draws a random card'''
        N = len(self.cards)
        i = random.randint(0,N-1)
        card = self.cards[i]
        self.cards.remove(card)
        return card

    def drawTwo(self,tot=False):
        '''draws two cards for player'''
        card1 = self.drawCard()
        card2 = self.drawCard()
        total = float(card1)+float(card2)
        if tot:
            return total
        else:
            return (card1,card2)

    def __repr__(self):
        '''prints this during call to print'''
        rStr = ""
        rStr += "Initial player sum: "+str(self.start[0])
        rStr += "\nDealer face card: "+str(self.start[1])
        rStr += "\nDealer hidden card: "+str(self.initDCards[1])
        rStr += "\nwinner must get to 21 or close\n"
        return rStr

    def __str__(self):
        return "{}:{}".format(self.hand[0], self.hand[1])