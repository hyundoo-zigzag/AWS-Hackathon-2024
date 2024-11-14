import re
import requests

class GoogleMapsAPI:
    def __init__(self, api_key):
        self.api_key=api_key
    
    # place_name를 기반으로 place_id 추출
    def get_place_id_from_name(self, place_name):
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": place_name,
            "key": self.api_key
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            if results:
                # 첫 번째 결과에서 place_id 추출
                place_id = results[0].get("place_id")
                if place_id:
                    return place_id
        return None

    # place_id를 기반으로 위도 및 경도 추출 함수
    def get_lat_lng_from_place_id(self, place_id):
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "geometry",  # geometry 필드를 통해 위도와 경도를 요청
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            location = response.json().get("result", {}).get("geometry", {}).get("location", {})
            lat, lng = location.get("lat"), location.get("lng")
            return f"{lat},{lng}"
        else:
            return None
    
    def extract_lat_lng_from_url(self, url):
        match = re.search(r'@([-+]?\d*\.\d+),([-+]?\d*\.\d+)', url)
        if match:
            lat, lng = match.groups()
            return f"{lat},{lng}"
        else:
            print("Error: URL에서 좌표를 찾을 수 없습니다.")
            return None
        
    # 상세 정보 및 리뷰 추출 함수 정의
    def get_place_details(self, place_id):
        url = f"https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "formatted_address,reviews",  # 주소, 별점, 리뷰 필드 요청
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json().get("result", {})
            address = result.get("formatted_address", "")
            reviews = [review.get("text", "") for review in result.get("reviews", [])]
            return address, reviews
        else:
            return None, []
        
    def get_nearby_places(self, location, place_type, radius, rankby="prominence"):
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            "location": location,  # 'latitude,longitude' 형식
            "radius": radius,      # 검색 반경 (미터 단위)
            "type": place_type,    # 장소 유형 (예: restaurant, hotel, amusement_park 등)
            "rankby": rankby,      # 결과 정렬 기준
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return results[:10]  # 상위 10개 장소 반환
        else:
            return None

    # Directions API를 활용한 경로 추출 함수
    def get_directions(self, start_place_id, end_place_id):
        # 출발지 좌표 추출
        start_location = self.get_lat_lng_from_place_id(start_place_id)
        if start_location is None:
            print('Cannot Find Start Location')
            return []

        # 도착지 좌표 추출
        end_location = self.get_lat_lng_from_place_id(end_place_id)
        if end_location is None:
            print('Cannot Find End Location')
            return []
        
        # 경로 요청
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": start_location,
            "destination": end_location,
            "mode": "transit",  # 이동 수단 설정 가능 (driving, walking, bicycling, transit)
            "key": self.api_key
        }
        
        response = requests.get(url, params=params)
        response_data = response.json()  # 응답 데이터 출력
        
        # 응답 상태 확인
        if response.status_code == 200:
            status = response_data.get("status")
            if status != "OK":
                print(f"Error: {status}")
                return []
            
            routes = response_data.get("routes", [])
            if not routes:
                print("No routes found.")
                return []
            
            legs = routes[0].get("legs", [])
            if not legs:
                print("No legs found in route.")
                return []
            
            steps = legs[0].get("steps", [])
            if not steps:
                print("No steps found in leg.")
                return []
            
            directions_list = []
            for step in steps:
                # 기본적인 방향과 거리, 시간
                instructions = step["html_instructions"]
                distance = step["distance"]["text"]
                duration = step["duration"]["text"]
                
                # transit 관련 정보가 있을 경우 버스 번호 등 상세 경로 추가
                if "transit_details" in step:
                    transit = step["transit_details"]
                    line = transit.get("line", {})
                    vehicle_type = line.get("vehicle", {}).get("type", "")
                    bus_number = line.get("short_name", "N/A")
                    directions_list.append(f"{instructions} - {distance}, {duration}, Bus Number: {bus_number} ({vehicle_type})")
                else:
                    directions_list.append(f"{instructions} - {distance}, {duration}")
            
            return directions_list
        else:
            assert "경로를 찾지 못했습니다."