import random


class SchemePolicy:

    def __init__(self):

        self.success_counts = {}
        self.total_counts = {}

    def select_scheme(self, schemes):

        epsilon = 0.1

        if random.random() < epsilon:
            return random.choice(schemes)

        best_scheme = None
        best_score = -1

        for s in schemes:

            success = self.success_counts.get(s, 0)
            total = self.total_counts.get(s, 1)

            score = success / total

            if score > best_score:
                best_score = score
                best_scheme = s

        return best_scheme