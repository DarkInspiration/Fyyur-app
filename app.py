#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import logging
from logging import FileHandler, Formatter

import babel
import dateutil.parser
from flask import (Flask, Response, flash, redirect, render_template, request,
                   url_for, jsonify)
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import Form
from oauthlib.uri_validate import query

import config
from forms import *

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String)
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship('Show', backref='venue', lazy=True)

    def __repr__(self):
        return f'<Venue id {self.id}, {self.name}>'

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String)
    image_link = db.Column(db.String(500))
    website = db.Column(db.String(120))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String)
    shows = db.relationship('Show', backref='artist', lazy=True)

    def __repr__(self):
        return f'<Artist id {self.id}, {self.name}>'


class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Venue id {self.venue_id}, artist_id {self.artist_id}>'


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')

#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    query = Venue.query.group_by(Venue.id, Venue.state, Venue.city).order_by('city', 'id').all()
    state_city = ''

    # Group same city venues
    for i in query:
        past_shows, upcoming_shows = get_upcoming_shows(venue_id= i.id)
        if state_city == i.city + i.state:
            data[len(data) - 1]["venues"].append({
                "id": i.id,
                "name": i.name,
                "num_upcoming_shows": len(upcoming_shows) if upcoming_shows else 0
            })
        else:
            state_city = i.city + i.state
            data.append({
                "city": i.city,
                "state": i.state,
                "venues": [{
                    "id": i.id,
                    "name": i.name,
                    "num_upcoming_shows": len(upcoming_shows) if upcoming_shows else 0
                }]
            })
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    response = {'data': []}
    searching_for = request.form.get('search_term')
    # Ilike to search no matter capitalization
    query = Venue.query.filter(Venue.name.ilike(f'%{searching_for}%'))
    response['count'] = query.count()

    for i in query:
        past_shows, upcoming_shows = get_upcoming_shows(venue_id= i.id)
        response['data'].append({'id': i.id, 'name': i.name, "num_upcoming_shows": len(upcoming_shows) if upcoming_shows else 0})
    return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    query = Venue.query.get(venue_id)
    past_shows, upcoming_shows = get_upcoming_shows(venue_id= venue_id)
    past_shows_data = []
    upcoming_shows_data = []

    # Go trough response and append shows details
    if past_shows:
        for i in past_shows:
            past_shows_data.append({
                "artist_id": i.artist_id,
                "artist_name": db.session.query(Artist.name).filter_by(id=i.artist_id).first()[0],
                "artist_image_link": db.session.query(Artist.image_link).filter_by(id=i.artist_id).first()[0],
                "start_time": str(i.start_time)
            })

    if upcoming_shows:
        for i in upcoming_shows:
            upcoming_shows_data.append({
                "artist_id": i.artist_id,
                "artist_name": db.session.query(Artist.name).filter_by(id=i.artist_id).first()[0],
                "artist_image_link": db.session.query(Artist.image_link).filter_by(id=i.artist_id).first()[0],
                "start_time": str(i.start_time)
            })

    #Workaround for genres showing
    split_genres = (query.genres[1:-1]).split(',')
    data = {
        "id": query.id,
        "name": query.name,
        "genres": split_genres,
        "address": query.address,
        "city": query.city,
        "state": query.state,
        "phone": query.phone,
        "website": query.website,
        "facebook_link": query.facebook_link,
        "seeking_talent": query.seeking_talent,
        "seeking_description": query.seeking_description,
        "image_link": query.image_link,
        "past_shows": past_shows_data,
        "upcoming_shows": upcoming_shows_data,
        "past_shows_count": len(past_shows) if past_shows else 0,
        "upcoming_shows_count": len(upcoming_shows) if upcoming_shows else 0
    }
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm()
    try:
        #Get data from form and use it to populate Venue table
        data = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data,
            website=form.website.data,
            # Auto add bool depending if there is a description or not (avoids user having to toggle a button)
            seeking_talent= True if form.seeking_description.data else False,
            seeking_description=form.seeking_description.data,
        )
        db.session.add(data)
        db.session.commit()
        flash(f'Venue {form.name.data} was successfully listed!')
    # Preventing FlaskWTFDeprecationWarning to trigger exceptions
    except (not Warning):
        db.session.rollback()
        flash(f'Venue {form.name.data}  was not successfully listed!')
    finally:
        db.session.close()
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        to_delete = Venue.query.filter_by(id=venue_id).first()
        #Get name of venue to delete so we can flas it
        venue_name = to_delete.name
        db.session.delete(to_delete)
        db.session.commit()
        flash(f'Venue {venue_name} was successfully deleted!')
    except:
        db.session.rollback()
        flash(f'Venue {venue_name} was successfully deleted!')
    finally:
        db.session.close()
    return jsonify({ 'sucess': True })

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = []
    query = Artist.query.order_by('id').all()
    for i in query:
        data.append({'id': i.id, 'name': i.name})
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    response = {'data': []}
    searching_for = request.form.get('search_term')
    query = Artist.query.filter(Artist.name.ilike(f'%{searching_for}%'))
    response['count'] = query.count()
    for i in query:
        past_shows, upcoming_shows = get_upcoming_shows(artist_id = i.id)
        response['data'].append({'id': i.id, 'name': i.name, 'num_upcoming_shows': len(upcoming_shows) if upcoming_shows else 0})
    return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    query = Artist.query.get(artist_id)
    past_shows, upcoming_shows = get_upcoming_shows(artist_id= artist_id)
    past_shows_data = []
    upcoming_shows_data = []

    if past_shows:
        for i in past_shows:
            past_shows_data.append({
                "venue_id": i.venue_id,
                "venue_name": db.session.query(Venue.name).filter_by(id=i.venue_id).first()[0],
                "venue_image_link": db.session.query(Venue.image_link).filter_by(id=i.venue_id).first()[0],
                "start_time": str(i.start_time)
            })

    if upcoming_shows:
        for i in upcoming_shows:
            upcoming_shows_data.append({
                "venue_id": i.venue_id,
                "venue_name": db.session.query(Venue.name).filter_by(id=i.venue_id).first()[0],
                "venue_image_link": db.session.query(Venue.image_link).filter_by(id=i.venue_id).first()[0],
                "start_time": str(i.start_time)
            })
    #Workaround for genres showing
    split_genres = (query.genres[1:-1]).split(',')

    #Could just return whole query as data, but this way we can control what do we send
    data = {
        "id": query.id,
        "name": query.name,
        "genres": split_genres,
        "city": query.city,
        "state": query.state,
        "phone": query.phone,
        "website": query.website,
        "facebook_link": query.facebook_link,
        "seeking_venue": query.seeking_venue,
        "seeking_description": query.seeking_description,
        "image_link": query.image_link,
        "past_shows": past_shows_data,
        "upcoming_shows": upcoming_shows_data,
        "past_shows_count": len(past_shows) if past_shows else 0,
        "upcoming_shows_count": len(upcoming_shows) if upcoming_shows else 0
    }
    return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    #Populating all the data in the edit dialog with query
    query = Artist.query.get(artist_id)
    #Workaround for sending genres
    split_genres = (query.genres[1:-1]).split(',')
    #Sending selected fields to the form so we can see them selected in the view
    form = ArtistForm(state=query.state, genres=split_genres, seeking_description=query.seeking_description)
    return render_template('forms/edit_artist.html', form=form, artist=query)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm()
    try:
        query = Artist.query.get(artist_id)
        query.name = form.name.data
        query.city= form.city.data
        query.state= form.state.data
        query.phone= form.phone.data
        query.genres= form.genres.data
        query.facebook_link= form.facebook_link.data
        query.image_link= form.image_link.data
        query.website= form.website.data
        query.seeking_description= form.seeking_description.data,
        query.seeking_venue= True if form.seeking_description.data else False
        db.session.add(query)
        db.session.commit()
        flash('Artist was successfully edited!')
    # Preventing FlaskWTFDeprecationWarning to trigger exceptions
    except (not Warning):
        db.session.rollback()
        flash('Artist was not successfully edited!')
    finally:
        db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    query = Venue.query.get(venue_id)
    #Workaround for sending genres
    split_genres = (query.genres[1:-1]).split(',')
    form = VenueForm(state=query.state, genres=split_genres, seeking_description=query.seeking_description)
    return render_template('forms/edit_venue.html', form=form, venue=query)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    form = VenueForm()
    try:
        query = Venue.query.get(venue_id)
        query.name = form.name.data
        query.city= form.city.data
        query.state= form.state.data
        query.address= form.address.data
        query.phone= form.phone.data
        query.genres= form.genres.data
        query.facebook_link= form.facebook_link.data
        query.image_link= form.image_link.data
        query.website= form.website.data
        query.seeking_talent= True if form.seeking_description.data else False
        query.seeking_description= form.seeking_description.data
        db.session.add(query)
        db.session.commit()
        flash('Artist was successfully edited!')
    # Preventing FlaskWTFDeprecationWarning to trigger exceptions
    except (not Warning):
        db.session.rollback()
        flash('Artist was not successfully edited!')
    finally:
        db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm()
    try:
        data = Artist(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data,
            website=form.website.data,
            seeking_venue= True if form.seeking_description.data else False,
            seeking_description=form.seeking_description.data
        )
        
        db.session.add(data)
        db.session.commit()
        flash(f'Artist {form.name.data} was successfully listed!')
    # Preventing FlaskWTFDeprecationWarning to trigger exceptions
    except (not Warning):
        db.session.rollback()
        flash(f'Artist {form.name.data}  was not successfully listed!')
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    data = []
    query = Show.query.order_by(Show.start_time).all()
    for i in query:
        data.append({
            "venue_id": i.venue_id,
            "venue_name": db.session.query(Venue.name).filter_by(id=i.venue_id).first()[0],
            "artist_id": i.artist_id,
            "artist_name": db.session.query(Artist.name).filter_by(id=i.artist_id).first()[0],
            "artist_image_link": db.session.query(Artist.image_link).filter_by(id=i.artist_id).first()[0],
            "start_time": str(i.start_time)
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm()
    try:
        data = Show(
            artist_id=form.artist_id.data,
            venue_id=form.venue_id.data,
            start_time=str(form.start_time.data)
        )
        db.session.add(data)
        db.session.commit()
        flash('Show was successfully listed!')
    # Preventing FlaskWTFDeprecationWarning to trigger exceptions
    except (not Warning):
        db.session.rollback()
        flash('Show was not successfully listed!')
    finally:
        db.session.close()
        return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

''' 
The connection between artists, venues and shows
If we get artist id we will return shows for given artist
If we get venue id we will return shows for given venue
Shows will be returned in touple - past shows and upcoming shows
'''
def get_upcoming_shows(artist_id= None, venue_id= None):
    today = datetime.now()
    if artist_id:
        query = Show.query.filter(Show.artist_id == artist_id).all()
        past_shows = []
        upcoming_shows = []
        if query:
            for i in query:
                if i.start_time > today:
                    upcoming_shows.append(i)
                else:
                    past_shows.append(i)
        return past_shows, upcoming_shows 
    if venue_id:
        query = Show.query.filter(Show.venue_id == venue_id).all()
        past_shows = []
        upcoming_shows = []
        if query:
            for i in query:
                if i.start_time > today:
                    upcoming_shows.append(i)
                else:
                    past_shows.append(i)
        return past_shows, upcoming_shows 

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
