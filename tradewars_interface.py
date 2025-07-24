"""Simplified Tradewars interface used by BBMesh."""

import random

# Per-player game states
_player_states = {}


def _new_game(node_id):
    """Initialize a new game state."""
    _player_states[node_id] = {
        "sector": 1,
        "credits": 1000,
        "step": "start",
    }


def play_tradewars(node_id: int, cmd: str) -> str:
    """Handle a single tradewars command.

    This is a very small wrapper that mimics the behaviour of the real
    Tradewars game. It keeps state in a module level dictionary and
    returns a string response for the BBS to send back to the user.

    Parameters
    ----------
    node_id: int
        Unique node identifier of the player.
    cmd: str
        Command text provided by the player. A blank string is used when
        the player first enters the game.

    Returns
    -------
    str
        Text that should be sent back to the user.
    """
    state = _player_states.get(node_id)
    if state is None:
        _new_game(node_id)
        return (
            "Welcome to TradeWars!\n"
            "(M)ove  (C)heck stats  E(X)IT"
        )

    cmd = cmd.strip().lower()
    if cmd == "x":
        _player_states.pop(node_id, None)
        return "Exiting TradeWars."
    elif cmd.startswith("m"):
        # Move to a random neighbouring sector
        state["sector"] += random.randint(1, 5)
        return f"Warped to sector {state['sector']}."
    elif cmd == "c":
        return f"Sector {state['sector']} - Credits: {state['credits']}"
    else:
        return "Unknown command. (M)ove, (C)heck, or E(X)IT"

