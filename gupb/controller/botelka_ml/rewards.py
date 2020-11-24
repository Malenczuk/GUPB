from gupb.controller.botelka_ml.wisdom import State
from gupb.controller.botelka_ml.model import MAPPING
from gupb.model.characters import Action


def calculate_reward(old_state: State, new_state: State, old_action_no: int) -> int:
    points = old_state.tick

    actions_list = MAPPING[old_action_no]

    if old_state.health != new_state.health:
        # Lost health
        points -= 1

    if old_state.can_attack_enemy and Action.ATTACK in actions_list:
        # Could attack enemy, and attacked enemy
        points += 20

    if old_state.visible_enemies > 0:
        # Sees enemies, the more the better
        points += old_state.visible_enemies

    return points
