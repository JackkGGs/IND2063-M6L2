import random

class Pokemon:
    def __init__(self, name, power, hp):
        self.name = name  # Fix: Consistent naming (changed from nm)
        self.hp = hp
        self.max_hp = hp  # For healing and tracking max HP
        self.power = power  # Fix: Consistent naming (changed from pwr)
        
    def attack(self, target):
        damage = random.randint(self.power - 5, self.power + 5)
        target.hp -= damage
        if target.hp < 0:
            target.hp = 0
        return damage
    
    def is_alive(self):
        return self.hp > 0

    def add_win(self):
        self.wins += 1

        # Bonus setelah menang ke-5
        if self.wins == 5:
            self.pokemon.increase_stats(hp_increase=10, power_increase=5)
    
    def heal(self, amount):
        """Heal Pokemon but don't exceed max HP"""
        self.hp = min(self.hp + amount, self.max_hp)
    
    def increase_stats(self, hp_increase, power_increase):
        """Increase both max HP and power when winning"""
        self.max_hp += hp_increase
        self.hp += hp_increase
        self.power += power_increase
    
    def decrease_stats(self, hp_decrease, power_decrease):
        """Decrease both max HP and power when losing, with minimums"""
        self.max_hp = max(50, self.max_hp - hp_decrease)
        self.hp = max(10, self.hp - hp_decrease)
        self.power = max(5, self.power - power_decrease)

class Player:
    def __init__(self, name, pokemon):
        self.name = name  # Fix: Consistent naming (changed from nm)
        self.pokemon = pokemon
        self.wins = 0
        self.losses = 0
        
    def attack_enemy(self, enemy):
        return self.pokemon.attack(enemy.pokemon)
    
    def add_win(self):
        self.wins += 1
        if self.wins % 5 == 0:
            self.pokemon.increase_stats(10, 5)
        
    def add_loss(self):
        self.losses += 1

class Enemy:
    def __init__(self, name, pokemon):
        self.name = name
        self.pokemon = pokemon