import os
import requests
import pandas as pd
import urllib.request
import uuid
import datetime
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get environment variables
api_key = os.getenv('GOOGLE_PLACES_API_KEY')
location = os.getenv('LOCATION')
query = os.getenv('QUERY')

def get_place_details(api_key, place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={api_key}"
    response = requests.get(url).json()
    return response.get('result', {})

def get_places(api_key, location, query, radius=5600, max_results=10):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query={query}&location={location}&radius={radius}&key={api_key}"
    results = []
    while True:
        response = requests.get(url).json()
        results.extend(response.get('results', []))
        if 'next_page_token' not in response or len(results) >= max_results:
            break
        url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?pagetoken={response['next_page_token']}&key={api_key}"
    return results[:max_results]

def download_image(api_key, photo_reference, venue_uuid, image_name, image_folder="images", max_width=1280):
    if not os.path.exists(image_folder):
        os.makedirs(image_folder)
    
    photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={max_width}&photoreference={photo_reference}&key={api_key}"
    image_filename = f"{image_name}_{venue_uuid}.jpg"
    image_path = os.path.join(image_folder, image_filename)
    
    # Download the image
    urllib.request.urlretrieve(photo_url, image_path)
    
    return image_path

def save_to_csv(venues, venue_images, venue_opening_hours):
    venues_df = pd.DataFrame(venues)
    venue_images_df = pd.DataFrame(venue_images)
    venue_opening_hours_df = pd.DataFrame(venue_opening_hours)

    venues_filename = f"{query}_venues.csv"
    venue_images_filename = f"{query}_venue_images.csv"
    venue_opening_hours_filename = f"{query}_venue_opening_hours.csv"
    
    # Save venues data
    venues_df.to_csv(venues_filename, index=False)
    
    # Save venue images data
    venue_images_df.to_csv(venue_images_filename, index=False)
    
    # Save venue opening hours data
    venue_opening_hours_df.to_csv(venue_opening_hours_filename, index=False)

def main():
    places = get_places(api_key, location, query)
    
    venues_data = []
    venue_images_data = []
    venue_opening_hours_data = []
    
    created_at = datetime.datetime.now()

    for place in places:
        place_id = place.get('place_id')
        details = get_place_details(api_key, place_id)
        
        # Generate a unique ID for the venue
        venue_id = uuid.uuid4()
        
        # Extracting venue details
        editorial_summary = details.get('editorial_summary', {})
        overview = editorial_summary.get('overview', '')

        venue = {
            "id": str(venue_id),
            "slug": details.get('name', '').lower().replace(" ", "-"),
            "name": details.get('name'),
            "venue_type_id": str(uuid.uuid4()),
            "summary": overview,
            "description": overview,
            "address": details.get('formatted_address', ''),
            "phone_number": details.get('formatted_phone_number', ''),
            "email_address": None,
            "website": details.get('website', ''),
            "instagram": None,
            "facebook": None,
            "price_level": details.get('price_level', 'N/A'),
            "user_ratings_total": details.get('user_ratings_total', 0),
            "created_at": created_at
        }
        venues_data.append(venue)
        
        # Download and save the image if available
        if 'photos' in details:
            for photo in details['photos']:
                photo_reference = photo['photo_reference']
                image_name = details['place_id']
                image_path = download_image(api_key, photo_reference, venue_id, image_name, "images", max_width=1280)
                
                # Prepare venue image data
                venue_image = {
                    "id": str(uuid.uuid4()),
                    "venue_id": str(venue_id),
                    "image_url": os.path.basename(image_path),
                    "featured": True,
                    "description": f"Image of {details.get('name', '')}",
                    "created_at": created_at
                }
                venue_images_data.append(venue_image)
        
        # Prepare venue opening hours data
        if 'opening_hours' in details:
            for day, hours in enumerate(details['opening_hours'].get('weekday_text', [])):
                # Example format: "Monday: 9:00 AM – 5:00 PM"
                if ' – ' in hours:
                    day_name, time_range = hours.split(": ")
                    time_range = time_range.strip()
                    
                    if ' – ' in time_range:
                        open_time, close_time = time_range.split(" – ")
                        
                        opening_time = datetime.datetime.strptime(open_time, "%I:%M %p").time() if open_time != "Closed" else None
                        closing_time = datetime.datetime.strptime(close_time, "%I:%M %p").time() if close_time != "Closed" else None
                        
                        opening_hour = {
                            "id": str(uuid.uuid4()),
                            "venue_id": str(venue_id),
                            "week_day": day,
                            "opening_time": opening_time,
                            "closing_time": closing_time,
                            "created_at": created_at
                        }
                        venue_opening_hours_data.append(opening_hour)
    
    save_to_csv(venues_data, venue_images_data, venue_opening_hours_data)
    print(f"Data saved to {query}_venues.csv, {query}_venue_images.csv, and {query}_venue_opening_hours.csv. Images are stored in the 'images' folder.")

if __name__ == "__main__":
    main()