import json
import dateutil.parser
import babel
from flask import (Flask, abort, render_template, request, Response, flash,
                   redirect, url_for)
from flask_moment import Moment
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from forms import *
from models import db, Artist, Show, Venue

# workaround fpr python 3.10+
import collections
collections.Callable = collections.abc.Callable


app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


def format_shows_data(shows):
    return [{'artist_id': show.artist.id,
             'artist_name': show.artist.name,
             'artist_image_link': show.artist.image_link,
             'venue_id': show.venue.id,
             'venue_name': show.venue.name,
             'venue_image_link': show.venue.image_link,
             'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S')
             } for show in shows]


def format_shows_for_artist(shows):
    return [{'venue_id': show.venue.id,
             'venue_name': show.venue.name,
             'venue_image_link': show.venue.image_link,
             'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S')
             } for show in shows]


def format_shows_for_venue(shows):
    return [{'artist_id': show.artist.id,
             'artist_name': show.artist.name,
             'artist_image_link': show.artist.image_link,
             'start_time': show.start_time.strftime('%Y-%m-%d %H:%M:%S')
             } for show in shows]


def format_artist_data(artist):
    data = artist.__dict__
    shows = get_shows_for_artist(artist)
    data.update(shows)

    return data


def format_artists_search_result(artists):
    results = []

    for artist in artists:
        shows = get_shows_for_artist(artist)
        results.append({'id': artist.id,
                        'name': artist.name,
                        'num_upcoming_shows': shows['upcoming_shows_count']})

    return results


def format_venue_data(venue):
    data = venue.__dict__
    shows = get_shows_for_venue(venue)
    data.update(shows)

    return data


def format_venues_search_result(venues):
    results = []

    for venue in venues:
        shows = get_shows_for_venue(venue)
        results.append({'id': venue.id,
                        'name': venue.name,
                        'num_upcoming_shows': shows['upcoming_shows_count']})

    return results


def get_shows_for_artist(artist):
    shows = Show.query.join(Artist).filter(Show.artist_id == artist.id)

    past_shows = shows.filter(Show.start_time <= datetime.now()).all()
    upcoming_shows = shows.filter(Show.start_time > datetime.now()).all()

    return {'past_shows': format_shows_for_artist(past_shows),
            'past_shows_count': len(past_shows),
            'upcoming_shows': format_shows_for_artist(upcoming_shows),
            'upcoming_shows_count': len(upcoming_shows)}


def get_shows_for_venue(venue):
    shows = Show.query.join(Venue).filter(Show.venue_id == venue.id)

    past_shows = shows.filter(Show.start_time <= datetime.now()).all()
    upcoming_shows = shows.filter(Show.start_time > datetime.now()).all()

    return {'past_shows': format_shows_for_venue(past_shows),
            'past_shows_count': len(past_shows),
            'upcoming_shows': format_shows_for_venue(upcoming_shows),
            'upcoming_shows_count': len(upcoming_shows)}


@app.route('/')
def index():
    return render_template('pages/home.html')


@app.route('/venues')
def venues():
    areas = []

    venue_states_cities = db.session.query(Venue.state, Venue.city)
    venue_groups = venue_states_cities.group_by(Venue.state, Venue.city).all()

    for group in venue_groups:
        venues_in_group = Venue.query.filter_by(state=group.state,
                                                city=group.city).all()

        venues = []
        for venue in venues_in_group:
            shows = get_shows_for_venue(venue)
            num_upcoming_shows = shows['upcoming_shows_count']
            venues.append({'id': venue.id,
                           'name': venue.name,
                           'num_upcoming_shows': num_upcoming_shows})

        areas.append({'city': group.city,
                      'state': group.state,
                      'venues': venues})

    return render_template('pages/venues.html', areas=areas)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')
    venues = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
    results = {'count': len(venues),
               'data': format_venues_search_result(venues)}

    return render_template('pages/search_venues.html', results=results,
                           search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

    if not venue:
        abort(404)

    data = format_venue_data(venue)

    return render_template('pages/show_venue.html', venue=data)


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    form = VenueForm(request.form, meta={'csrf': False})

    if form.validate():
        try:
            venue = Venue(name=form.name.data,
                          city=form.city.data,
                          state=form.state.data,
                          address=form.address.data,
                          phone=form.phone.data,
                          genres=form.genres.data,
                          website_link=form.website_link.data,
                          seeking_talent=form.seeking_talent.data,
                          seeking_description=form.seeking_description.data,
                          image_link=form.image_link.data,
                          facebook_link=form.facebook_link.data)

            db.session.add(venue)
            db.session.commit()

        except Exception:
            error = True
            db.session.rollback()

        finally:
            db.session.close()

    else:
        error = True

    if error:
        flash('An error occurred. Venue ' + request.form['name']
              + ' could not be listed.', 'error')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')

    return render_template('pages/home.html')


@app.route('/venues/<venue_id>/delete', methods=['GET', 'DELETE'])
def delete_venue(venue_id):
    error = False

    try:
        venue = Venue.query.filter(Venue.id == venue_id).one_or_none()
        venue_name = venue.name
        db.session.delete(venue)
        db.session.commit()

    except Exception:
        error = True
        db.session.rollback()

    finally:
        db.session.close()

    if error:
        flash(f'An error occurred. Venue {venue_name} could not be deleted.',
              'error')
    else:
        flash(f'Venue {venue_name} was successfully deleted!')
    return render_template('pages/home.html')


@app.route('/artists')
def artists():
    artists = Artist.query.all()

    return render_template('pages/artists.html', artists=artists)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')
    artists = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()
    results = {'count': len(artists),
               'data': format_artists_search_result(artists)}

    return render_template('pages/search_artists.html', results=results,
                           search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

    if not artist:
        abort(404)

    data = format_artist_data(artist)

    return render_template('pages/show_artist.html', artist=data)


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

    if not artist:
        abort(404)

    form = ArtistForm(obj=artist)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    error = False
    artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

    try:
        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.genres = request.form.getlist('genres')
        artist.image_link = request.form['image_link']
        artist.facebook_link = request.form['facebook_link']
        artist.website_link = request.form['website_link']
        seeking_venue = True if 'seeking_venue' in request.form else False
        artist.seeking_venue = seeking_venue
        artist.seeking_description = request.form['seeking_description']

        db.session.commit()

    except Exception:
        error = True
        db.session.rollback()

    finally:
        db.session.close()

    if error:
        flash('An error occurred. Artist could not be updated.')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully updated!')

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

    if not venue:
        abort(404)

    form = VenueForm(obj=venue)

    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    error = False
    venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

    try:
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.genres = request.form.getlist('genres')
        venue.image_link = request.form['image_link']
        venue.facebook_link = request.form['facebook_link']
        venue.website_link = request.form['website_link']
        seeking_talent = True if 'seeking_talent' in request.form else False
        venue.seeking_talent = seeking_talent
        venue.seeking_description = request.form['seeking_description']

        db.session.commit()

    except Exception:
        error = True
        db.session.rollback()

    finally:
        db.session.close()

    if error:
        flash('An error occurred. Venue could not be updated.')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully updated!')

    return redirect(url_for('show_venue', venue_id=venue_id))


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False

    form = ArtistForm(request.form, meta={'csrf': False})
    if form.validate():
        try:
            artist = Artist(name=form.name.data,
                            city=form.city.data,
                            state=form.state.data,
                            phone=form.phone.data,
                            genres=form.genres.data,
                            website_link=form.website_link.data,
                            seeking_venue=form.seeking_venue.data,
                            seeking_description=form.seeking_description.data,
                            image_link=form.image_link.data,
                            facebook_link=form.facebook_link.data)

            db.session.add(artist)
            db.session.commit()

        except Exception:
            error = True
            db.session.rollback()

        finally:
            db.session.close()

    else:
        error = True

    if error:
        flash('An error occurred. Artist ' + request.form['name']
              + ' could not be listed.', 'error')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')

    return render_template('pages/home.html')


@app.route('/shows')
def shows():
    shows = Show.query.all()

    data = format_shows_data(shows)

    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    form = ShowForm(request.form, meta={'csrf': False})

    if form.validate():
        try:
            show = Show(artist_id=form.artist_id.data,
                        venue_id=form.venue_id.data,
                        start_time=form.start_time.data)

            db.session.add(show)
            db.session.commit()

        except Exception:
            error = True
            db.session.rollback()

        finally:
            db.session.close()

    else:
        error = True

    if error:
        flash('An error occurred. Show could not be listed.', 'error')
    else:
        flash('Show was successfully listed!')

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    s = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    file_handler.setFormatter(
        Formatter(s)
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


if __name__ == '__main__':
    app.run()
