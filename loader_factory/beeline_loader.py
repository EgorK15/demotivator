import datetime
from datetime import datetime, timezone
import time
import requests
import os
from dotenv import load_dotenv
import logging
from pandas import DataFrame
from mutagen.mp3 import MP3
logging.basicConfig(level=logging.INFO, filename="../logs.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
from loader_factory.abstract_loader import AbstractLoader
'''
     9677692248-Смоляков
     9649841121-Сулейманов
     9608279603-Косян
     9677696381-Краснов
     9677623376-Джафаров
     9063429149-Бутянин
     9063436490-Харитонов
     9639106079-Алмин
     9063433554-Трунин
     9033043006-Вагин
     9679205889-Мамонтов
'''
class BeelineLoader(AbstractLoader):
    load_dotenv()
    users=[user for user in os.getenv("BEELINE_USERS").split(',')]
    beeline_key=os.getenv("BEELINE_KEY")
    def get_calls(self,period,current_time,user):
            start = datetime.fromtimestamp(current_time - period, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end = datetime.fromtimestamp(current_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            user=user
            response=requests.request('GET',f'https://cloudpbx.beeline.ru/apis/portal/records?userId={user}&dateFrom={start}&dateTo={end}',headers={'X-MPBX-API-AUTH-TOKEN':BeelineLoader.beeline_key})
            response.raise_for_status()
            return response.json()
    def get_recording(self,url):
        response=requests.request("GET",f'https://cloudpbx.beeline.ru/apis/portal/v2/records/{url}/download',headers={'X-MPBX-API-AUTH-TOKEN':BeelineLoader.beeline_key})
        response.raise_for_status()
        return response
    def get_users(self):
        response=requests.request('GET',f'https://cloudpbx.beeline.ru/apis/portal/abonents',headers={'X-MPBX-API-AUTH-TOKEN':BeelineLoader.beeline_key})
        response.raise_for_status()
        return response.json()

    def clear_directory(self,dir_path):
        for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    if os.path.isfile(file_path):
                            os.remove(file_path)
    def get_recording_safely(self,url):
        timer=0
        count=0
        while count<5:
                try:
                    count+=1
                    timer+=60
                    recording = BeelineLoader.get_recording(self,url)
                except Exception as e:
                    logging.error('Beeline inner error:', str(e))
                    pass
                else:
                    return recording
                time.sleep(timer)
        raise Exception("Failed to get recording")
    def get_calls_safely(self,period,current_time,user):
        timer=0
        count=0
        while count<5:
                try:
                    count+=1
                    timer+=60
                    calls = BeelineLoader.get_calls(self,period,current_time,user)
                except Exception as e:
                    logging.error('Beeline inner error:', str(e))
                    pass
                else:
                    return calls
                time.sleep(timer)
        raise Exception("Failed to get calls")
    def loader(self,period,current_time):
        df = DataFrame(
                columns=["Agent_Name", "Client_Number",
                        "Employee_Number", "EmployeeId",
                        "Time_Started", "Time_Ended",
                        "RecordingID","Direction","Duration"]
                        )
        count = 0
        flag=False
        empty=True
        for user in BeelineLoader.users:
                    call_stats=BeelineLoader.get_calls_safely(self,period,current_time,user)
                    print("Balls")
                    if call_stats:
                        empty=False
                        for call in call_stats:
                                if call['id'] and call['duration']>30:
                                    direction='outgoing' if call['direction'] == 'OUTBOUND' else 'incoming'
                                    flag=True
                                    recording=BeelineLoader.get_recording_safely(self,call['id'])
                                    with open(f"loader_factory/mp3/{count}.mp3", "wb") as f:
                                        f.write(recording.content)
                                    audio_file=MP3(f"loader_factory/mp3/{count}.mp3")
                                    duration=audio_file.info.length
                                    if duration>30:
                                        flag=False
                                        start = datetime.fromtimestamp(int(str(call['date'])[:10]), tz=timezone.utc)
                                        end = datetime.fromtimestamp(int(str(call['date'])[:10]) + int(duration),
                                                                     tz=timezone.utc)
                                        df.loc[len(df)] = [str(call['abonent']['lastName']) + ' ' + str(call['abonent']['firstName']), call["phone"],call['abonent']['phone'],call['abonent']['userId'],
                                                                                start,end,call['id'],direction,
                                                                                int(duration)]
                                        count+=1
        if flag:
            os.remove(f"loader_factory/mp3/{count}.mp3")
        if empty:
            logging.info("Beeline empty")
        else:
            df.to_csv(f"loader_factory/csv/all.csv", encoding='utf-8')
            logging.info("Beeline ready")

    mp3_path = r"loader_factory/mp3"
    csv_path = r"loader_factory/csv"
    '''
    language = "ru"
    prompt_file_name = "prompt_file_auto.txt"
    checklist_file_name = "check_list_auto.json"
    '''
    def main(self,time_from):
        print(time_from)
        if time_from<0: raise Exception("Negative value")
        current_time=time.time()
        timer=0
        while True:
            try:
                timer+=120
                BeelineLoader.loader(self,time_from,current_time)
            except Exception as e:
                mp3_path = self.mp3_path
                csv_path = self.csv_path
                BeelineLoader.clear_directory(self,mp3_path)
                BeelineLoader.clear_directory(self,csv_path)
                logging.error('Beeline error:', str(e))
                pass
            else:
                break
            time.sleep(timer)

    def dicks(self, numb, results,audio,id):
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
    loader=BeelineLoader()
    loader.main(1800)