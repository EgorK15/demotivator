#temporary_loader
import requests
import hashlib
import time
import json
import pandas as pd
from dotenv import load_dotenv
from mutagen.mp3 import MP3
from pandas import DataFrame
from io import StringIO
import numpy as np
import logging
import os
logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
import datetime
from datetime import datetime


# recording_id = id записи
# start= время начала разговора
# finish= время конца разговора
# from_extension = id звонящего сотрудника
# from_number = номер звонящего
# to_extension = id сотрудника, принимающего звонок
# to_number = номер принимающего звонок
# disconnect_reason = причина отключения
class MangoLoader:
    load_dotenv()
    employeeId = [int(id) for id in os.getenv('EMPLOYEE_ID').split(',')]

    key = os.getenv('MANGO_KEY')
    salt = os.getenv('MANGO_SALT')
    mp3_path = r"LoaderFactory/mp3"
    csv_path = r"LoaderFactory/csv"
    '''
    language = "ru"
    prompt_file_name = "prompt_file_optics.txt"
    checklist_file_name = "check_list_optics.json"
    '''

    def generate_sign(self,api_key: str, api_salt: str, json_data: dict = None) -> str:
        string = f"{api_key}{json.dumps(json_data) if json_data else ''}{api_salt}"
        return hashlib.sha256(string.encode()).hexdigest()


    def generate_nu_sign(self,api_key: str, api_salt: str, recording_id: str, timestamp: str) -> str:
        string = f"{api_key}{timestamp}{recording_id}{api_salt}"
        return hashlib.sha256(string.encode()).hexdigest()


    def get_call_stats_to(self,api_key: str, api_salt: str, time_from: int,current_time, extension: int) -> dict:
        url = 'https://app.mango-office.ru/vpbx/stats/request'
        json_data = {
            'date_from': (int(current_time - time_from)),
            'date_to': (int(current_time)),
            'to': {
                'extension': extension,
            },
            'fields': "records, start, finish, from_extension, from_number, to_extension, to_number, disconnect_reason",
            'request_id': f"request{int(current_time)}"
        }
        data = {
            'vpbx_api_key': api_key,
            'sign': MangoLoader.generate_sign(self,api_key, api_salt, json_data),
            'json': json.dumps(json_data)
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()


    def get_call_stats_from(self,api_key: str, api_salt: str, time_from: int, current_time, extension: int) -> dict:
        url = 'https://app.mango-office.ru/vpbx/stats/request'
        json_data = {
            'date_from': (int(current_time - time_from)),
            'date_to': (int(current_time)),
            'from': {
                'extension': extension,
            },
            'fields': "records, start, finish, from_extension, from_number, to_extension, to_number, disconnect_reason",
            'request_id': f"request{int(current_time)}"
        }
        data = {
            'vpbx_api_key': api_key,
            'sign': MangoLoader.generate_sign(self,api_key, api_salt, json_data),
            'json': json.dumps(json_data)
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()


    def get_request_status(self,api_key: str, api_salt: str, key: str) -> dict:
        url = 'https://app.mango-office.ru/vpbx/stats/result'
        json_data = {'key': key}
        data = {
            'vpbx_api_key': api_key,
            'sign': MangoLoader.generate_sign(self,api_key, api_salt, json_data),
            'json': json.dumps(json_data)
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        if response.status_code == 204:
            time.sleep(30)
            df = MangoLoader.get_request_status(self,api_key, api_salt, key)
            if not df.empty:
                return df
        TESTDATA = StringIO(response._content.decode("utf-8"))
        colnames = ["recording_id", "start", "finish", "from_extension", "from_number", "to_extension", "to_number",
                    "disconnect_reason"]
        df = pd.read_csv(TESTDATA, sep=";", names=colnames, header=None)
        return df


    def get_recording(self,recording_id,api_key: str=key, api_salt: str=salt, action: str = 'download') -> dict:
        timestamp=int(time.time() + 10000000000)
        url = f"https://app.mango-office.ru/vpbx/queries/recording/link/{recording_id}/{action}/{api_key}/{timestamp}/{MangoLoader.generate_nu_sign(self,api_key, api_salt, recording_id, timestamp)}"
        response = requests.get(url)
        response.raise_for_status()
        return response


    def get_worker(self,api_key: str, api_salt: str, extension: str) -> dict:
        url = 'https://app.mango-office.ru/vpbx/config/users/request'
        json_data = {'extension': extension}
        data = {
            'vpbx_api_key': api_key,
            'sign': MangoLoader.generate_sign(self,api_key, api_salt, json_data),
            'json': json.dumps(json_data)
        }
        response = requests.post(url, data)
        response.raise_for_status()
        return json.loads(response._content.decode("utf-8"))


    def clear_directory(self,dir_path):
        for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    if os.path.isfile(file_path):
                            os.remove(file_path)


    def get_result_safely(self,from_key,to_key):
        count=0
        timer=0
        while count<5:
            try:
                timer+=60
                result_to = MangoLoader.get_request_status(self,MangoLoader.key, MangoLoader.salt, to_key)
                result_from = MangoLoader.get_request_status(self,MangoLoader.key, MangoLoader.salt, from_key)
                result = pd.concat([result_from, result_to], join="inner", axis=0, ignore_index=True)
            except Exception as e:
                logging.error('Mango inner error:', str(e))
                pass
            else:
                return result
            time.sleep(timer)
        raise Exception("Failed to get stats")


    def records_standartization(self,records):
        records = records.replace("[", "")
        records = records.replace("]", "")
        records = records.split(',')
        return records

    def get_worker_safely(self,key,salt,i):
        timer=0
        count=0
        while count<5:
                try:
                    count+=1
                    timer+=60
                    work = MangoLoader.get_worker(self,key, salt, str(i))
                except Exception as e:
                    logging.error('Mango inner error:', str(e))
                    pass
                else:
                    return work
                time.sleep(timer)
        raise Exception("Failed to get worker")

    def get_recording_safely(self,record):
        count=0
        timer=0
        while count<5:
            try:
                count+=1
                timer+=15
                recording=MangoLoader.get_recording(self,record)
            except Exception as e:
                logging.error('Mango inner error:', str(e))
                pass
            else:
                return recording
            time.sleep(timer)
        raise Exception("Failed to get recording")
    def get_from_call_stats_safely(self,time_from,current_time,i):
            count=0
            timer=0
            while count<5:
                try:
                    count+=1
                    timer+=60
                    stats_response_from = MangoLoader.get_call_stats_from(self,MangoLoader.key, MangoLoader.salt, time_from,current_time, i)
                except Exception as e:
                    logging.error('Mango inner error:', str(e))
                    pass
                else:
                    return stats_response_from
                time.sleep(timer)
            raise Exception("Failed to get stats from")
    def get_to_call_stats_safely(self,time_from,current_time,i):
            count=0
            timer=0
            while count<5:
                try:
                    count+=1
                    timer+=60
                    stats_response_to = MangoLoader.get_call_stats_to(self,MangoLoader.key, MangoLoader.salt, time_from,current_time, i)
                except Exception as e:
                    logging.error('Mango inner error:', str(e))
                    pass
                else:
                    return stats_response_to
                time.sleep(timer)
            raise Exception("Failed to get stats to")
    def loader(self,time_from,current_time):
            df = DataFrame(
                columns=["Agent_Name", "Client_Number",
                        "Employee_Number", "EmployeeId",
                        "Time_Started", "Time_Ended",
                        "RecordingID","Direction"]
                        )
            k = 0
            for i in MangoLoader.employeeId:
                time.sleep(2)
                print('Запрашиваем статистику...')
                work = MangoLoader.get_worker_safely(self,MangoLoader.key, MangoLoader.salt, i)
                employee_number = work["users"][0]["telephony"]["outgoingline"]
                stats_response_to = MangoLoader.get_to_call_stats_safely(self,time_from,current_time, i)
                time.sleep(2)
                stats_response_from = MangoLoader.get_from_call_stats_safely(self,time_from,current_time, i)
                print('Получен ключ запроса:', stats_response_to)
                if 'key' in stats_response_to:
                    if 'key' in stats_response_from:
                        flag=False
                        print('Запрашиваем результат...')
                        result = MangoLoader.get_result_safely(self,stats_response_from["key"],stats_response_to["key"])
                        print('Результат:', result)
                        if not result.empty:
                            for row in range(0, len(result.index)):
                                to_ext = np.isnan(result["from_extension"][row])
                                from_ext = np.isnan(result["to_extension"][row])
                                if from_ext != to_ext and (result['finish'][row]-result["start"][row])>30:
                                    records = str(result["recording_id"][row])
                                    records = MangoLoader.records_standartization(self,records)
                                    direction = "Входящий" if to_ext else "Исходящий"
                                    if records[0] != "":
                                        for record in records:
                                            if record!="":
                                                flag=True
                                            client_number = 0
                                            if to_ext:
                                                client_number = int(result["from_number"][row])
                                            else:
                                                client_number = int(result["to_number"][row])
                                            recording = MangoLoader.get_recording_safely(self,record)
                                            with open(f"LoaderFactory/mp3/{k}.mp3", "wb") as f:
                                                f.write(recording.content)
                                            audio_file=MP3(f"LoaderFactory/mp3/{k}.mp3")
                                            duration=audio_file.info.length
                                            if duration>30:
                                                flag=False
                                                df.loc[len(df)] = [work["users"][0]["general"]["name"], client_number,
                                                            employee_number, i,
                                                            datetime.fromtimestamp(result["start"][row]),
                                                            datetime.fromtimestamp(result["finish"][row]),
                                                                record,direction]
                                                k += 1
                                            time.sleep(1)
                            if flag:
                                os.remove(f"LoaderFactory/mp3/{k}.mp3")
                        else:
                            logging.info("Mango empty")
            logging.info("Mango ready")
            df.to_csv(f"LoaderFactory/csv/all.csv", encoding='utf-8')



    def main(self,time_from):
        current_time=time.time()
        if time_from<0: raise Exception("Negative value")
        timer=0
        while True:
            try:
                timer+=120
                self.loader(time_from,current_time)
            except Exception as e:
                mp3_path = self.mp3_path
                csv_path= self.csv_path
                self.clear_directory(mp3_path)
                self.clear_directory(csv_path)
                logging.error('Mango error:', str(e))
                pass
            else:
                 break
            time.sleep(timer)

    def dicks(self, numb, results,audio,id):
        audio_file = MP3(audio)
        duration = audio_file.info.length
        direct_dict = {"Исходящий": "outgoing", "Входящий": "incoming"}
        direct = direct_dict[results["Direction"][numb]]
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
    loader=MangoLoader()
    loader.main(30000)