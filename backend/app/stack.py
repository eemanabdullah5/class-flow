class EmptyStackError(Exception):
    """Raised by pop() and peek() when there is nothing on the stack."""


class Stack:
    """A last-in, first-out (LIFO) stack, like a pile of plates.

    push() puts an item on top, peek() looks at the top item, and pop() takes it off.
    The last item pushed is always the first one back. Used for grade undo:
    the newest grade change is the first one to be undone.
    """

    def __init__(self, items=None):
        # The end of the list is the top of the stack, so push and pop are fast.
        self._items = list(items) if items is not None else []

    def push(self, item) -> None:
        self._items.append(item)

    def pop(self):
        if self.is_empty():
            raise EmptyStackError("The stack is empty.")
        return self._items.pop()

    def peek(self):
        if self.is_empty():
            raise EmptyStackError("The stack is empty.")
        return self._items[-1]

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def __len__(self) -> int:
        return len(self._items)
