from aiogram.fsm.state import State, StatesGroup


class PromoStates(StatesGroup):
    choosing_mode = State()
    waiting_mask = State()
    waiting_file = State()
    waiting_single_code = State()

