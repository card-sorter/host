TASK_NAME = "Sort Cards"
TASK_DESCRIPTION = "Sort already scanned cards"

from typing import List
import cv2
import numpy as np
from controller.tasks.task import *
from pyzbar.pyzbar import decode
import aiohttp

class CardObj:
    def __init__(self, value: int):
        self.value = value

    def __repr__(self):
        return f"Card({self.value})"

class Stack:
    def __init__(self, capacity: int, name: str):
        self.capacity = capacity
        self.name = name
        self._cards: List[CardObj] = []

    @property
    def empty(self) -> bool:
        """Checks if the stack is empty."""
        return len(self._cards) == 0

    @property
    def full(self) -> bool:
        """Checks if the stack is full."""
        return len(self._cards) == self.capacity

    def push(self, card: CardObj):
        """Pushes a card onto the stack."""
        if self.full:
            raise OverflowError(f"Stack {self.name} is full")
        self._cards.append(card)

    @property
    def sorted(self) -> bool:
        """Checks if the stack is sorted."""
        if self.empty:
            return False
        return self._cards == sorted(self._cards, key=lambda card: card.value)

    def pop(self) -> CardObj:
        """Pops a card from the stack."""
        if self.empty:
            raise IndexError(f"Stack {self.name} is empty")
        return self._cards.pop()

    @property
    def peek(self) -> CardObj:
        """Returns the top card without removing it."""
        if self.empty:
            raise IndexError(f"Stack {self.name} is empty")
        return self._cards[-1]

    def __len__(self):
        return len(self._cards)

    def __repr__(self):
        return f"Stack({self.name}, size={len(self._cards)}/{self.capacity})"

    def __contains__(self, card: CardObj):
        for c in self._cards:
            if c.value == card.value:
                return True
        return False

class GreedyDigSort:
    def __init__(self, stacks: List[Stack], sorted_values: List[int]):
        self.stacks = stacks
        self.sorted_values = sorted_values
        self.sorted_target_stack = None
        self.moves = []

    def move(self, source: Stack, target: Stack):
        """
        Moves a card from the source stack to the target stack.
        """
        self.moves.append((self.stacks.index(source), self.stacks.index(target)))
        target.push(source.pop())

    def find_dig_target(self, source: Stack):
        """
        Finds the target stack for the dig operation.
        """
        smallest_stack = min([s for s in self.stacks if not s.full and s != self.sorted_target_stack and s != source], key=lambda s: len(s))
        return smallest_stack

    def dig(self, source: Stack, card: CardObj):
        """
        Digs a card from the source stack
        """
        while source.peek.value != card.value:
            self.move(source, self.find_dig_target(source))

    def find_sort_target(self):
        """
        Finds the target stack for the sort operation.
        """
        # Find smallest stack that's not sorted
        smallest_stack = min([s for s in reversed(self.stacks) if not s.sorted], key=lambda s: len(s))
        # Empty it
        while not smallest_stack.empty:
            self.move(smallest_stack, self.find_dig_target(smallest_stack))
        
        self.sorted_target_stack = smallest_stack

    def find_card_stack(self, card: CardObj):
        """
        Finds the stack containing the specified card.
        """
        for s in self.stacks:
            if card in s:
                return s
        return None

    def sort(self):
        """
        Main entry point for the greedy dig sort algorithm.
        """
        self.find_sort_target()
        for c in self.sorted_values:
            self.dig(self.find_card_stack(CardObj(c)), CardObj(c))
            self.move(self.find_card_stack(CardObj(c)), self.sorted_target_stack)
            if self.sorted_target_stack.full:
                self.find_sort_target()
        return self.moves
    

class Sort(TaskController):
    def __init__(self, ctx: TaskContext):
        super().__init__(ctx)

    def scan_barcode(self, image: np.ndarray):
        barcodes = decode(image)
        for b in barcodes:
            return b.data.decode('utf-8')
        return None

    async def scan_api(self, image: np.ndarray):
            data = aiohttp.FormData()
            data.add_field('image',
                        image,
                        filename='image.jpg',
                        content_type='image/jpeg')
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:8000/scan", data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        text = await response.text()
                        print(json.dumps(text, indent = 4))
                        raise Exception(f"failed to scan with status {response.status}: {response.text}")

    async def run(self):
        # scan top card of every bin, find an empty one
        bins = self.ctx.bins
        # stack of len -1 because they will never be full
        stacks = [Stack(-1, str(b.x)) for b in self.ctx.bins]
        all = []
        target = None
        source_bins = []
        # 1 : len(bins) + 1 because bin 0 is the camera bin so it doesn't have any cards
        # default bins is bins without the camera bin
        for b in range(1, len(self.ctx.default_bins)+1):
            img = await self.ctx.hal.scan_card(bins[b], bins[b])
            barcode = self.scan_barcode(img)
            if barcode:
                # load bin from db
                bins[b].barcode = barcode
                bins[b].id = await self.ctx.database.check_barcode(barcode)
                if bins[b].id:
                    bins[b].clear()
                    #b.extend(await self.ctx.database.load_bin(b.id))
                    bins[b].scanned = True
                    if bins[b].empty:
                        target = b
                else:
                    target = b
            else:
                source_bins.append(b)
        print("part 2")
        print(source_bins)
        if not target:
            return
        for b in source_bins:
            while True:
                img = await self.ctx.hal.scan_card(bins[b], bins[target])
                barcode = self.scan_barcode(img)
                if barcode:
                    # move barcode back to the bin it came from
                    # the barcode means that it's at the bottom of the bin, so we move on
                    await self.ctx.hal.move_card(bins[target], bins[b])
                    bins[target].scanned = True
                    target = b
                    break
                success, encoded = cv2.imencode('.jpg', img)
                image_bytes = encoded.tobytes()
                card = await self.scan_api(image_bytes)
                cardObj = CardObj(card[0]['details']['product_id'])
                stacks[target].push(cardObj)
                all.append(cardObj.value)
                bins[target].append(card[0]['details']['name'])
        print(self.ctx.default_bins)
        all.sort()
        sorter = GreedyDigSort(stacks, all)
        moves = sorter.sort()
        print(len(moves))
        for move in moves:
            print(move)
            print(await self.ctx.hal.move_card(bins[move[0]], bins[move[1]]))
        print(self.ctx.default_bins)

__all__ = ['Sort']
