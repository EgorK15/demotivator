import datetime
from datetime import datetime, timezone
import time
import requests
from dotenv import load_dotenv
import logging
from pandas import DataFrame
from mutagen.mp3 import MP3
import os

from LoaderFactory.abstract_loader import AbstractLoader
logging.basicConfig(level=logging.INFO, filename='logs.log', filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
class KCellLoader(AbstractLoader):
    load_dotenv()
    users=[user for user in os.getenv("KCELL_USERS").split(',')]
    kcell_key=os.getenv("KCELL_KEY")
    def get_user(self):
        data={
            'with':'status'
        }
        response=requests.request('GET',f'https://actualoptic.vpbx.kcell.kz/crmapi/v1/users/muslima',data=data,headers={'X-API-KEY':KCellLoader.kcell_key})
        response.raise_for_status()
        return response.json()
    def get_calls(self,period,current_time,user):
            start = datetime.fromtimestamp(current_time-period, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            end = datetime.fromtimestamp(current_time, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            user=user
            response=requests.request('GET',f'https://actualoptic.vpbx.kcell.kz/crmapi/v1/history/json?user={user}&start={start}&end={end}',headers={'X-API-KEY':KCellLoader.kcell_key})
            response.raise_for_status()
            return response.json()
    def get_recording(self,url):
        response=requests.request("GET",url,headers={'X-API-KEY':KCellLoader.kcell_key})
        response.raise_for_status()
        return response
    def get_users(self):
        response=requests.request('GET',f'https://actualoptic.vpbx.kcell.kz/crmapi/v1/users',headers={'X-API-KEY':KCellLoader.kcell_key})
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
                    recording = KCellLoader.get_recording(self,url)
                except Exception as e:
                    logging.error('KCell inner error:', str(e))
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
                    calls = KCellLoader.get_calls(self,period,current_time,user)
                except Exception as e:
                    logging.error('KCell inner error:', str(e))
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
        for user in KCellLoader.users:
                    call_stats=KCellLoader.get_calls_safely(self,period,current_time,user)
                    if call_stats:
                        empty=False
                        for call in call_stats:
                            if call['status']!='noanswer':
                                if call['record'] and call['duration']>30:
                                    flag=True
                                    recording=KCellLoader.get_recording_safely(self,call['record'])
                                    with open(f"LoaderFactory/mp3/{count}.mp3", "wb") as f:
                                        f.write(recording.content)
                                    audio_file=MP3(f"LoaderFactory/mp3/{count}.mp3")
                                    duration=audio_file.info.length
                                    if duration>30:
                                        direction="outgoing" if call['type']=='out' else 'incoming'
                                        flag=False
                                        start = datetime.strptime(call['start'], "%Y-%m-%dT%H:%M:%SZ")
                                        start = start.replace(tzinfo=timezone.utc)
                                        end = datetime.fromtimestamp(start.timestamp() + call['duration'],
                                                                     tz=timezone.utc)
                                        df.loc[len(df)] = [call['user_name'], call["client"],call['diversion'],call['user'],
                                                                                start.timestamp(),end,call['record'],direction,
                                                                                call['duration']]
                                        count+=1
        if flag:
            os.remove(f"LoaderFactory/mp3/{count}.mp3")
        if empty:
            logging.info("KCell empty")
        else:
            df.to_csv(f"LoaderFactory/csv/all.csv", encoding='utf-8')
            logging.info("KCell ready")

    mp3_path = r"LoaderFactory/mp3"
    csv_path = r"LoaderFactory/csv"

    '''govno dlya egorika
    language = "kk"
    prompt_file_name = "prompt_file_optics.txt"
    checklist_file_name = "check_list_optics.json"
    '''

    def main(self,time_from):
        if time_from<0: raise Exception("Negative value")
        current_time=time.time()
        timer=0
        while True:
            try:
                timer+=120
                KCellLoader.loader(self,time_from,current_time)
            except Exception as e:
                mp3_path = self.mp3_path
                csv_path = self.csv_path
                self.clear_directory(dir_path= mp3_path)
                self.clear_directory(dir_path=csv_path)
                logging.error('KCell error:', str(e))
                pass
            else:
                break
            time.sleep(timer)

    def dicks(self,numb,results,audio,id):
        duration = int(results['Duration'][numb])
        direct = results["Direction"][numb]
        sample_call_data = {
        "call_id": id,
        "caller_number": str(results["Employee_Number"][numb]),
        "callee_number": str(results["Client_Number"][numb]),
        "call_timestamp": datetime.fromtimestamp(results["Time_Started"][numb]),
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
    loader=KCellLoader()
    loader.main(1800)