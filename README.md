# Daylight Wallpaper

Daylight wallpaper is a simple Python program that switches the system wallpaper depending on the time of the day: before sunrise, a mostly dark wallpaper is applied, and before sunset, the wallpaper is mostly white.

Simply because having to wear sunglasses by night to work is enough as it is. I need darkness.

As the wallpapers are the color inverted versions of each other, this program features a nice fading effect because I really don't need to f e e l the sunrise with the screen blasting white light at my face at 7am.

## Specs

Written entirely in python, this program makes calls to the [Sunrise-Sunset API](https://sunrise-sunset.org/) to retrieve the appropriate values, then calculates the delta between these times and the current time to change, or not, the wallpaper.

Since it is intended to be called once an hour, only the first iteration of the program reaches the API, and then saves the data for later.

Oh, and the cool dude on the wallpapers is Joker from Persona 5.

## How to use

Use crontab or windows task planner to trigger the start of the program once an hour. It's not the most accurate version right now, maybe I'll update it later so that the wallpaper changes at the right times.
