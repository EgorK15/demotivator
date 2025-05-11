import os
from dotenv import load_dotenv
from pandas import DataFrame
import pandas as pd
import requests
import datetime
from datetime import datetime, timezone, timedelta
from io import StringIO
import time
import logging

logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
from LoaderFactory.abstract_loader import AbstractLoader

load_dotenv()

# мегадупер прокси через мск (мб уедет в .env)
API_URL = 'http://ruproxy.abc-call.ru/megaphone/'
# отличается от API_URL, если нужно проксировать
ORIGINAL_URL = 'https://lift-prom.megapbx.ru/'

class Megaphone_Loader(AbstractLoader):
    mp3_path = r"LoaderFactory/mp3"
    csv_path = r"LoaderFactory/csv"
    megaphone_key = os.getenv('MEGAPHONE_KEY')
    headers = {'X-API-KEY': f'{megaphone_key}'}
    # Define server timezone (adjust as needed, e.g., for Moscow: UTC+3)
    server_timezone = timezone(timedelta(hours=3))  # Moscow timezone

    def clear_directory(self, dir_path):
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

    def get_worker(self, login):
        url = f'{API_URL}/crmapi/v1/users/{login}'
        response = requests.get(url=url, headers=Megaphone_Loader.headers, stream=True)
        response.raise_for_status()
        user_name = response.json()['name']
        return user_name

    def get_recording(self, recording_url):
        response = requests.get(url=recording_url, headers=Megaphone_Loader.headers)
        response.raise_for_status()
        return response

    def get_calls(self, time_from):
        # Convert timestamp to datetime with UTC timezone
        dt_from = datetime.fromtimestamp(time_from, tz=timezone.utc)
        # Format the time string in the required format
        time_str = dt_from.strftime('%Y%m%dT%H%M%SZ')
        print(time_str)
        url = f'{API_URL}/crmapi/v1/history/csv?limit=100&start={time_str}'
        response = requests.get(url=url, headers=Megaphone_Loader.headers, stream=True)
        response.raise_for_status()
        return response.text

    def get_calls_safely(self, time_from):
        count = 0
        timer = 0
        while count < 5:
            try:
                count += 1
                timer += 60
                result = Megaphone_Loader.get_calls(self, time_from)
            except Exception as e:
                logging.error(f'Megaphone inner error: {str(e)}')
                pass
            else:
                return result
            time.sleep(timer)
        raise Exception("Failed to get calls")

    def get_worker_safely(self, login):
        count = 0
        timer = 0
        while count < 5:
            try:
                count += 1
                timer += 60
                result = Megaphone_Loader.get_worker(self, login)
            except Exception as e:
                logging.error(f'Megaphone inner error: {str(e)}')
                pass
            else:
                return result
            time.sleep(timer)
        raise Exception("Failed to get employee name")

    def get_recording_safely(self, record):
        count = 0
        timer = 0
        while count < 5:
            try:
                count += 1
                timer += 15
                recording = Megaphone_Loader.get_recording(self, record)
            except Exception as e:
                logging.error(f'Mango inner error: {str(e)}')
                pass
            else:
                return recording
            time.sleep(timer)
        raise Exception("Failed to get recording")

    def loader(self, time_from):
        df_phones = DataFrame(columns=["Agent_Name", "Client_Number",
                                       "Employee_Number", "EmployeeId",
                                       "Time_Started", "Time_Ended",
                                       "RecordingID", "Direction", "Duration"])

        call_result = Megaphone_Loader.get_calls_safely(self, time_from)
        if call_result != '':
            f = StringIO(call_result)
            df = pd.read_csv(f, names=['id', 'type', 'phone_client', 'email_user',
                                       'phone_employee', 'started', 'wait_duration',
                                       'duration', 'recording_url'])
            i = 0
            for index, row in df.iterrows():
                if row['recording_url'] != '' and row['duration'] > 30:
                    login = row['email_user'][:-21]
                    direction = 'outgoing' if row['type'] == 'out' else 'incoming'
                    user_name = Megaphone_Loader.get_worker_safely(self, login)

                    # Parse the time with timezone awareness
                    start_time = datetime.strptime(row['started'], '%Y-%m-%dT%H:%M:%SZ')
                    start_time = start_time.replace(tzinfo=timezone.utc)

                    # Convert to server timezone for display/storage
                    local_start_time = start_time.astimezone(self.server_timezone)

                    # Calculate end time properly with timezone
                    local_end_time = local_start_time + timedelta(seconds=row['duration'])

                    df_phones.loc[len(df_phones)] = [
                        user_name,
                        row['phone_client'],
                        row['phone_employee'],
                        login,
                        local_start_time,
                        local_end_time,
                        row['recording_url'].replace(ORIGINAL_URL, API_URL),
                        direction,
                        row['duration']
                    ]

                    recording = Megaphone_Loader.get_recording_safely(self, row['recording_url'].replace(ORIGINAL_URL, API_URL))
                    with open(f"LoaderFactory/mp3/{i}.mp3", "wb") as f:
                        f.write(recording._content)
                    i += 1

        df_phones.to_csv('LoaderFactory/csv/all.csv', index=False)

    def main(self, time_from):
        # Get current time in UTC
        current_time = datetime.now(timezone.utc).timestamp()
        if time_from < 0:
            raise Exception("Negative value")

        timer = 0
        while True:
            try:
                timer += 120
                self.loader(current_time - time_from)
            except Exception as e:
                mp3_path = self.mp3_path
                csv_path = self.csv_path
                self.clear_directory(mp3_path)
                self.clear_directory(csv_path)
                logging.error(f'Megaphone error: {str(e)}')
                pass
            else:
                break
            time.sleep(timer)

    def dicks(self, numb, results, audio, id):
        duration = int(results['Duration'][numb])
        direct = results["Direction"][numb]
        sample_call_data = {
            "call_id": id,
            "caller_number": str(results["Employee_Number"][numb]),
            "callee_number": str(results["Client_Number"][numb]),
            "call_timestamp": results["Time_Started"][numb],
            "direction": direct,
            "agent_id": str(results["EmployeeId"][numb]),
            "agent_name": results["Agent_Name"][numb],
            "recording_url": str(results["RecordingID"][numb]),
            "duration": duration,
            "status": "pending",
            "end_reason": ""
        }
        return sample_call_data

    def gettype(self, results, anal, numb):
        return anal["type"]


if __name__ == '__main__':
    loader = Megaphone_Loader()
    loader.main(20000)