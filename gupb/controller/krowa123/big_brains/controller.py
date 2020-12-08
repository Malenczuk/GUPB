import traceback

import numpy as np
from rl.agents import DQNAgent
from rl.memory import SequentialMemory
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Flatten, Dense, Input, Conv2D, MaxPool2D, GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam

from gupb.controller import Controller
from gupb.model import characters, arenas, tiles
from gupb.model.arenas import Arena
from gupb.model.characters import ChampionKnowledge, Action, Facing
from gupb.model.effects import Mist


class AiController(Controller):
    def __init__(self, uname):
        self.uname = uname
        self.knowledge = None
        self.menhir_position = None
        self.next_action = Action.DO_NOTHING

    @property
    def preferred_tabard(self) -> characters.Tabard:
        return characters.Tabard.VIOLET

    @property
    def name(self):
        return f"AiController_{self.uname}"

    def decide(self, knowledge: ChampionKnowledge):
        self.knowledge = knowledge
        return self.next_action

    def reset(self, arena_description: arenas.ArenaDescription) -> None:
        self.menhir_position = arena_description.menhir_position


class Ai2Controller(Controller):
    def __init__(self, uname):
        self.uname = uname
        self.menhir_position = None
        self.arena = None

        action_n = len(list(Action)) - 1

        model = create_model((10, 10, 7), action_n)

        memory = SequentialMemory(limit=50000, window_length=10)
        agent = DQNAgent(model=model, memory=memory, nb_actions=action_n, nb_steps_warmup=10)
        agent.compile(Adam(lr=1e-3), metrics=['mae'])
        agent.observations = []
        agent.actions = []
        # agent.load_weights("sarsa_weights.h5f")

        self.agent = agent


    @property
    def preferred_tabard(self) -> characters.Tabard:
        return characters.Tabard.VIOLET

    @property
    def name(self):
        return f"Ai2Controller_{self.uname}"

    def getFacing(self, facing: Facing):
        return {
            Facing.UP: 1,
            Facing.DOWN: 2,
            Facing.LEFT: 3,
            Facing.RIGHT: 4
        }[facing]

    def getWeapon(self, weapon: str):
        return {
            "amulet": 1,
            "axe": 2,
            "bow": 3,
            "knife": 4,
            "sword": 5
        }[weapon]

    def _get_state(self, knowledge: ChampionKnowledge):
        state = np.zeros((10, 10, 10), dtype=np.uint8)

        for coord, tile in self.arena.terrain.items():
            x, y = coord
            state[x, y, 0] = 1 if tile.terrain_passable() else 0
            state[x, y, 1] = 1 if tile.terrain_transparent() else 0
            state[x, y, 2] = 1 if any([isinstance(e, Mist) for e in tile.effects]) else 0

            if knowledge:
                if coord in knowledge.visible_tiles:
                    state[x, y, 3] = 1

                    character = knowledge.visible_tiles[coord].character
                    if character:
                        state[x, y, 4] = self.getFacing(character.facing)
                        state[x, y, 5] = character.health
                        state[x, y, 6] = self.getWeapon(character.weapon.name)

                    loot = knowledge.visible_tiles[coord].loot
                    if loot:
                        state[x, y, 7] = self.getWeapon(loot.name)

        if knowledge:
            xx, yy = knowledge.position
            state[xx, yy, 9] = 1
        xx, yy = self.menhir_position
        state[xx, yy, 8] = 1

        return state

    def decide(self, knowledge: ChampionKnowledge):
        try:
            state = self._get_state(knowledge)
            xd = self.agent.forward(state)
            action = list(Action)[xd]
            print(action)
            return action
        except Exception as e:
            traceback.print_exc()
        return Action.DO_NOTHING

    def reset(self, arena_description: arenas.ArenaDescription) -> None:
        self.menhir_position = arena_description.menhir_position
        self.arena = Arena.load(arena_description.name)
        self.arena.menhir_position = self.menhir_position
        self.arena.terrain[self.menhir_position] = tiles.Menhir()


def create_model(input_shape, action_n):
    model = Sequential()
    model.add(Input(input_shape))
    model.add(Conv2D(32, (3, 3), padding='same', activation='relu', data_format='channels_last'))
    model.add(Conv2D(64, (3, 3), padding='same', activation='relu', data_format='channels_last'))
    model.add(MaxPool2D(pool_size=(2, 2), data_format='channels_last'))
    model.add(Conv2D(64, (3, 3), activation='relu', data_format='channels_last'))
    model.add(Conv2D(128, (3, 3), activation='relu', data_format='channels_last'))
    model.add(GlobalAveragePooling2D(data_format='channels_last'))
    model.add(Dense(256, activation='relu'))
    model.add(Dense(256, activation='relu'))
    model.add(Dense(action_n, activation='linear'))

    return model
