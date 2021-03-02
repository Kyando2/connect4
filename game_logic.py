from random import randint, shuffle
import time
import datetime
import multiprocessing
import logging
import json
from itertools import chain

import pyglet.shapes as shapes
import pyglet.text as text

ADJACENCY_VECTORS = [
            (0,1),
            (1,0),
            (1,1),
            (0,-1),
            (-1,0),
            (-1,-1),
            (1,-1),
            (-1,1)
        ]

class GameState:
    def __init__(self, matrice, me):
        self.object_matrice = matrice
        self.state_matrice = {k: 0 for k in self.object_matrice.keys()}
        self.state = StateData(self.state_matrice)
        self.magic_converter = {(int(v.x), int(v.y)): k for k, v in self.object_matrice.items()}
        self.actives = []
        self.turn = 1
        self.calculating = None
        self.adjacency_vectors = [
            (0,1),
            (1,0),
            (1,1),
            (0,-1),
            (-1,0),
            (-1,-1),
            (1,-1),
            (-1,1)
        ]
        self.window = me

    def convert(self, obj):
        return self.magic_converter[(int(obj.x), int(obj.y))]

    def solve(self):
        self.board = Board(list(self.__object_matrice.keys()), self, self.defaults)
        self.solving = True
    
    def state_to_num(self):
        return "".join([str(k[0])+str(k[1])+str(v) for k, v in self.state_matrice.items()])

    def add(self, obj, aiplay=True):
        if self.turn == 3: return False
        if self.state.is_empty(self.convert(obj)):
            coord = self.state.move_from_x(self.convert(obj)[0])
            obj = self.object_matrice[coord]
            self.state.register_move(coord, self.turn)
            self.turn = 1 if self.turn == 2 else 2
            # Object creation
            new_obj = shapes.Circle(x=(obj.x)+(obj.width/2), y=(obj.y)+(obj.height/2), radius=obj.height/2, color=((255, 50, 50) if self.turn == 2 else (255, 255, 20)))
            self.actives.append(new_obj)
            self.find_line()
            # Make the AI play
            if aiplay and self.turn != 3:
                self.aifoundmove = multiprocessing.Array('i', [5,5])
                self.calculating = multiprocessing.Process(target=find_good_move, args=(self.state, self.turn, self.aifoundmove))
                self.calculating.start()
            else:
                return True
        return False
        
    def find_line(self):
        is_correct = lambda a : True if a[0]==a[1]==a[2]==a[3] and a[0] != 0 else False
        vector_sum = lambda a, b : list(map(sum, zip(a, b)))
        vector_multiple = lambda a, b: (a[0]*b[0], a[1]*b[1])
        state_tuple = lambda a : tuple([self.state_matrice[tuple(item)] if tuple(item) in self.state_matrice else 0 for item in a])
        generate_quartets = lambda a : [(a, vector_sum(a, vector), vector_sum(a, vector_multiple((2,2), vector)), vector_sum(a, vector_multiple((3,3), vector))) for vector in self.adjacency_vectors]
        for coord in self.state_matrice.keys(): 
            for quartet in generate_quartets(coord): 
                if is_correct(state_tuple(quartet)):
                    self.lineco = ((self.object_matrice[tuple(quartet[0])].x, self.object_matrice[tuple(quartet[0])].y), (self.object_matrice[tuple(quartet[3])].x, self.object_matrice[tuple(quartet[3])].y))
                    self.turn = 3 

        
class StateData:
    def __init__(self, matrice, highest=None):
        self.__matrice = matrice 
        self.__highest = [0]*7 if highest == None else highest

    def move_from_x(self, x):
        # x should be < 7
        if self.__highest[x] > 5:
            return False
        return (x, self.__highest[x])
    
    def get_pos(self, coords):
        if tuple(coords) not in self.__matrice: return False
        return self.__matrice[tuple(coords)]

    def register_move(self, coords, turn):
        if self.__matrice[coords] != 0:
            return False
        self.__matrice[coords] = turn
        self.__highest[coords[0]] = coords[1]+1
        self.most_recent = coords
        return True

    def is_empty(self, coords):
        return True if self.__matrice[coords] == 0 else False

    def __copy__(self):
        new_instance = type(self)(self.__matrice.copy(), self.__highest.copy())
        return new_instance

    def copy(self):
        return self.__copy__()

    @property
    def matrice(self):
        return self.__matrice

    def create_hypothetical_state_from_move(self, coords, move_initiator_turn):
        hypothetical_state = self.copy()
        move_was_registered = hypothetical_state.register_move(coords, move_initiator_turn)
        if not move_was_registered:
            return False
        return hypothetical_state

def win_check(state, turn, move):
    is_correct = lambda a : True if a[0]==a[1]==a[2]==a[3] and a[0] != 0 else False
    vector_sum = lambda a, b : list(map(sum, zip(a, b)))
    vector_multiple = lambda a, b: (a[0]*b[0], a[1]*b[1])
    state_tuple = lambda a : tuple([state.get_pos(tuple(item)) if state.get_pos(tuple(item)) != False else 0 for item in a])
    start_points = [func(vector, move) for vector in ADJACENCY_VECTORS for func in (lambda a, b: b, lambda a, b: vector_sum(a,b), lambda a, b: vector_sum(vector_multiple(a,(2,2)), b), lambda a, b: vector_sum(vector_multiple(a,(3,3)), b))]
    generate_quartets = lambda a : [(a, vector_sum(a, vector), vector_sum(a, vector_multiple((2,2), vector)), vector_sum(a, vector_multiple((3,3), vector))) for vector in ADJACENCY_VECTORS]
    for coord in start_points: 
        for quartet in generate_quartets(coord): 
            if is_correct(state_tuple(quartet)):
                return 1 if state.get_pos(quartet[0]) == turn else 2
    return 0

def find_good_move(state, turn, found_move, depth=1):
    hypothetical_states_iterator = create_hypothetical_states_iterator(state, turn)
    bad_moves = []
    possible_moves = []
    recommended = []
    ok = {}
    for hypothetical_state in hypothetical_states_iterator:
        bot_move = hypothetical_state.bot_move
        player_move = hypothetical_state.player_move
        if bot_move not in bad_moves:
            if (winner := win_check(hypothetical_state, turn, player_move)) == 1:
                found_move[0], found_move[1] = bot_move[0], bot_move[1]
                return True
            elif winner == 2:
                bad_moves.append(bot_move)
                if player_move[1] == 0 or (hypothetical_state.get_pos((below := (player_move[0], (player_move[1]-1)))) != 0 and bot_move != below): # checks if the move is actually possible for the bot to even in play
                    recommended.append(player_move)
                continue
            else:
                if depth > 0:
                    if find_good_move(hypothetical_state, turn, [0,0], depth-1) == False:
                        bad_moves.append(bot_move)
                        continue
                ok[bot_move] = ok[bot_move]+1 if bot_move in ok else 1
                if bot_move not in possible_moves:
                    possible_moves.append(bot_move)
                if ok[bot_move] > 6 and bot_move:
                    found_move[0], found_move[1] = bot_move[0], bot_move[1]
                    return True

    shuffle(recommended)
    for move in recommended:
        if move not in bad_moves:
            found_move[0], found_move[1] = move[0], move[1]
            return True
            
    shuffle(possible_moves)
    for move in possible_moves:
        if move not in bad_moves:
            found_move[0], found_move[1] = move[0], move[1]
            return True
    
    if len(recommended)>0: 
        found_move[0], found_move[1] = recommended[0][0], recommended[0][1]
    return False
        

def create_hypothetical_states_iterator(state: StateData, turn):
    hypothetical_states_iterator = []
    nums = range(7)
    shuffle(list(nums))
    for i in nums:
        if (move_coords := state.move_from_x(i)) == False:
            continue
        hypothetical_state = state.create_hypothetical_state_from_move(move_coords, turn) 
        if not hypothetical_state:
            continue
        nums2 = list(range(7))
        shuffle(nums2)
        for j in nums2:
            if (move_coords1 := state.move_from_x(j)) == False:
                continue
            if move_coords1 == move_coords:
                continue
            sub_hypothetical_state = state.create_hypothetical_state_from_move(move_coords1, (1 if turn == 2 else 2)) 
            if not sub_hypothetical_state:
                continue
            sub_hypothetical_state.bot_move = move_coords
            sub_hypothetical_state.player_move = move_coords1
            hypothetical_states_iterator.append(sub_hypothetical_state)
    return hypothetical_states_iterator


