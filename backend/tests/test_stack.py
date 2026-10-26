import pytest

from app.stack import EmptyStackError, Stack


def test_new_stack_is_empty():
    stack = Stack()

    assert stack.is_empty()
    assert len(stack) == 0


def test_items_come_back_last_in_first_out():
    stack = Stack()
    for item in ["A", "B", "C"]:
        stack.push(item)

    assert [stack.pop(), stack.pop(), stack.pop()] == ["C", "B", "A"]
    assert stack.is_empty()


def test_peek_shows_top_item_without_removing_it():
    stack = Stack()
    stack.push("A")
    stack.push("B")

    assert stack.peek() == "B"
    assert stack.peek() == "B"
    assert len(stack) == 2


def test_length_follows_pushes_and_pops():
    stack = Stack()
    stack.push("A")
    stack.push("B")
    stack.pop()

    assert len(stack) == 1
    assert not stack.is_empty()


def test_stack_can_start_from_a_list_oldest_first():
    # The last item in the list ends up on top, like pushing them in order.
    stack = Stack(["oldest", "middle", "newest"])

    assert stack.peek() == "newest"
    assert len(stack) == 3


def test_starting_list_is_copied_not_shared():
    items = ["A"]
    stack = Stack(items)
    stack.push("B")

    assert items == ["A"]


def test_pop_on_empty_stack_raises_clear_error():
    with pytest.raises(EmptyStackError):
        Stack().pop()


def test_peek_on_empty_stack_raises_clear_error():
    with pytest.raises(EmptyStackError):
        Stack().peek()
