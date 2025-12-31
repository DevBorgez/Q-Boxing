# Q-Boxing - A boxing fight with Q-Learning

First, you need to fill in the .env with the path to your images.

Then, run the main.py.

## What do the fighters do? ##
- They move around the map trying to get close to each other.
- They throw short, medium, or long punches.
- They attempt to dodge when they think they're about to be hit.
- They manage energy: if they use it all up, they become weak.
- They learn from what happens:
- If an action works, they tend to repeat it.
- If it doesn't work, they avoid it in the future.

## How does the game work? ##
- Each fight is divided into timed rounds.
- The round ends by: 
- Knockout or time running out.
- Whoever wins more rounds wins the game.

## Punches and dodges ##
- Punches have different ranges:
- Close → weak
- Medium → balanced
- Far → strong
- Hits cost energy.
- Dodging spends energy, but can avoid damage.

## Damage ##
- It's not fixed.
- Depends on: Energy, right distance and a little luck.
- Sometimes, a very rare and strong hit occurs ("Super Punch").

## General behavior ##
- Bots learn to:
Not stray too far,
Not punch out of range,
Not waste energy,
Press when the other is weak.
