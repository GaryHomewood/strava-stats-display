from flask import Flask, render_template, request
from PIL import Image, ImageDraw, ImageFont
from http import HTTPStatus
import json
import os
from datetime import datetime
import requests
import props
import time

app = Flask(__name__)
# Flask Cache disabling, in dev mode
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Platform detection to allow for protype sketching/hacking before deploy
is_raspberry_pi = os.uname()[4][:3] == 'arm'
if is_raspberry_pi:
  from inky import InkyPHAT

@app.route('/api/v1/refresh', methods = ['POST'])
def refresh():
  # Call Strava to get the stats as json
  stats = get_strava_stats()

  # Allow for light or dark mode
  req = request.json
  mode = ''
  if (req and 'mode' in req):
    mode = request.json['mode']

  if (mode == 'dark'):
    bg = 'black'
    text_colour = 'white'
  else:
    bg = 'white'
    text_colour = 'black'

  # Create an image with the stats
  img = Image.new('RGBA', (212, 104), bg)
  canvas = ImageDraw.Draw(img)
  canvas.text((4,1), f'{stats["year"]}', font=ImageFont.truetype(f'static/fonts/Roboto-Bold.ttf', 11), fill=text_colour)
  canvas.line((1, 16, 210, 16), fill=text_colour, width=2)
  canvas.text((4,26), "Runs", font=ImageFont.truetype(f'static/fonts/Roboto-Bold.ttf', 12), fill=text_colour)
  canvas.text((80,26), "Rides", font=ImageFont.truetype(f'static/fonts/Roboto-Bold.ttf', 12), fill=text_colour)
  canvas.text((160,26), "Swims", font=ImageFont.truetype(f'static/fonts/Roboto-Bold.ttf', 12), fill=text_colour)
  canvas.text((4,43), f'{stats["run"]["count"]}', font=ImageFont.truetype(f'static/fonts/Roboto-Light.ttf', 12), fill=text_colour)
  canvas.text((80,43), f'{stats["ride"]["count"]}', font=ImageFont.truetype(f'static/fonts/Roboto-Light.ttf', 12), fill=text_colour)
  canvas.text((160,43), f'{stats["swim"]["count"]}', font=ImageFont.truetype(f'static/fonts/Roboto-Light.ttf', 12), fill=text_colour)
  total_y = 63
  canvas.text((4,total_y), f'{stats["run"]["distance"]:,}m', font=ImageFont.truetype(f'static/fonts/Roboto-Regular.ttf', 22), fill=text_colour)
  canvas.text((80,total_y), f'{stats["ride"]["distance"]:,}m', font=ImageFont.truetype(f'static/fonts/Roboto-Regular.ttf', 22), fill=text_colour)
  canvas.text((160,total_y), f'{stats["swim"]["distance"]:,}m', font=ImageFont.truetype(f'static/fonts/Roboto-Regular.ttf', 22), fill=text_colour)
  canvas.line((2, 99, 210, 99), fill=text_colour, width=2)
  img_png = img.resize((212, 104))
  img_png.save('static/img/stats.png')

  if is_raspberry_pi:
    # Draw to the eInk display if there is one
    inky_display = InkyPHAT('black')
    img_pal = Image.new("P", (1,1))
    img_pal.putpalette((255, 255, 255, 0, 0, 0, 255, 0, 0) + (0, 0, 0) * 252)
    img_eink = img_png.convert("RGB").quantize(palette=img_pal)
    inky_display.set_image(img_eink.rotate(180))
    inky_display.show()

  return '', HTTPStatus.NO_CONTENT

@app.route('/')
def home():
  """
  Show the YTD Strava stats for an athlete.
  With a button to generate an image of the stats, and display on a Rapsberry Pi eInk.
  For the motivation.
  """
  stats = get_strava_stats()
  return render_template('index.html', stats=stats)

def get_strava_stats():
  """
  Get the YTD Strava stats for an athlete.
  Return a trimmed-down json response with just the totals, in miles.
  """
  # Get saved API tokens
  with open('strava_tokens.json') as check:
    strava_tokens = json.load(check)

  # If access_token has expired then use the refresh_token to get a new access_token
  if (strava_tokens != None) and (strava_tokens['expires_at'] < time.time()):
    # Make Strava auth API call with your client_id, client_secret and code
    response = requests.post(
                      url = 'https://www.strava.com/oauth/token',
                      data = {
                              'client_id': props.client_id,
                              'client_secret': props.client_secret,
                              'refresh_token': strava_tokens['refresh_token'],
                              'grant_type': 'refresh_token'
                              }
                            )

    # Save tokens to file
    new_strava_tokens = response.json()
    with open('strava_tokens.json', 'w') as outfile:
      json.dump(new_strava_tokens, outfile)

    # Use the new Strava tokens from now on
    strava_tokens = new_strava_tokens
    
  # Get athlete stats
  url = f'https://www.strava.com/api/v3/athletes/{props.athlete_id}/stats'
  access_token = strava_tokens['access_token']
  athlete_stats = requests.get(url + '?access_token=' + access_token).json()

  # Extract YTD number and distances converted to miles
  year = datetime.now().year
  run_count = athlete_stats['ytd_run_totals']['count']
  run_distance = int(round(athlete_stats['ytd_run_totals']['distance']/1609))
  ride_count = athlete_stats['ytd_ride_totals']['count']
  ride_distance = int(round(athlete_stats['ytd_ride_totals']['distance']/1609))
  swim_count = athlete_stats['ytd_swim_totals']['count']
  swim_distance = int(round(athlete_stats['ytd_swim_totals']['distance']/1609))
  stats = {
    "year": year,
    "run": {
      "count": run_count,
      "distance": run_distance,
    },
    "ride": {
      "count": ride_count,
      "distance": ride_distance,
    },
    "swim": {
      "count": swim_count,
      "distance": swim_distance,
    }
  }
  return json.loads(json.dumps(stats))