import requests
import time
from pandas import DataFrame
import datetime
from dateutil import parser
from mutagen.mp3 import MP3
from datetime import datetime
import logging
import os
from dotenv import load_dotenv


from loader_factory.abstract_loader import AbstractLoader
logging.basicConfig(level=logging.INFO, filename="logs.log", filemode="w",
                    format="%(asctime)s %(levelname)s %(message)s")
class SkorozvonLoader(AbstractLoader):
    load_dotenv()
    username=os.getenv("SKOROZVON_USERNAME")
    api_key=os.getenv("SKOROZVON_KEY")
    client_id=os.getenv("SKOROZVON_ID")
    client_secret=os.getenv("SKOROZVON_SECRET")
    def get_access_token(self):
        data={
            'grant_type':'password',
            'username':SkorozvonLoader.username,
            'api_key':SkorozvonLoader.api_key,
            'client_id':SkorozvonLoader.client_id,
            'client_secret':SkorozvonLoader.client_secret
        }
        response=requests.post('https://app.skorozvon.ru/oauth/token',data=data)
        response.raise_for_status()
        return response.json()
    def get_scenarios_res(self,access_id):
        response=requests.request('GET',f'https://app.skorozvon.ru/api/v2/scenarios/50000012927/results',headers={'Authorization':f'Bearer {access_id}'})
        return response.json()
    def get_user_res(self,access_id,id):
        response=requests.request('GET',f'https://app.skorozvon.ru/api/v2/users/{id}',headers={'Authorization':f'Bearer {access_id}'})
        response.raise_for_status()
        return response.json()
    def get_users(self,access_id):
        response=requests.request('GET',f'https://app.skorozvon.ru/api/v2/users',headers={'Authorization':f'Bearer {access_id}'})
        response.raise_for_status()
        return response.json()
    def get_calls(self,access_id,time_from,current_time):
        resultIDs = [int(id) for id in os.getenv('SKOROZVON_RESULT_IDS').split(',')]
        user_emails=[email for email in os.getenv('SKOROZVON_USERS').split(',')]
        filter={
            'results_ids':resultIDs,
            'scenarios_ids':'all',
            'tags_ids':'all',
            'types':'all',
            'users_emails':user_emails
        }
        data={
            'start_time':int(current_time-time_from),
            'end_time':int(current_time),
            'filter':filter,
            'length':1000
        }
        response=requests.request('POST',f'https://app.skorozvon.ru/api/reports/calls_total.json',json=data,headers={'Authorization':f'Bearer {access_id}'})
        response.raise_for_status()
        return response.json()
    '''
    default get_archive(url,access_id):
        response=requests.request("GET",url=url)
        if response.status_code == 404:
            time.sleep(30)
            df = get_archive(url,access_id)
            if df.status_code!=404:
                return df
        return response
    '''
    def get_recording(self,recording_id):
        access_token=SkorozvonLoader().get_access_token()['access_token']
        response=SkorozvonLoader().get_recording_loader(f'https://app.skorozvon.ru/api/calls/{recording_id}.mp3',access_token)
        return response
    def get_recording_loader(self,url,access_token):
        response=requests.request("GET",url+f'?access_token={access_token}')
        response.raise_for_status()
        return response
    def get_recording_safely(self,url,access_token):
        timer=0
        count=0
        while count<5:
                try:
                    count+=1
                    timer+=60
                    recording = SkorozvonLoader.get_recording_loader(self,url,access_token)
                except Exception as e:
                    logging.error('Skorozvon inner error:', str(e))
                    pass
                else:
                    return recording
                time.sleep(timer)
        raise Exception("Failed to get recording")
    def get_worker_safely(self,access_token,id):
        timer=0
        count=0
        while count<5:
                try:
                    count+=1
                    timer+=60
                    work = SkorozvonLoader.get_user_res(self,access_token,id)['short_number']
                except Exception as e:
                    logging.error('Skorozvon inner error:', str(e))
                    pass
                else:
                    return work
                time.sleep(timer)
        raise Exception("Failed to get worker")
    def get_calls_safely(self,access_token,time_from,current_time):
        timer=0
        count=0
        while count<5:
                try:
                    count+=1
                    timer+=60
                    calls = SkorozvonLoader.get_calls(self,access_token,time_from,current_time)
                except Exception as e:
                    logging.error('Skorozvon inner error:', str(e))
                    pass
                else:
                    return calls
                time.sleep(timer)
        raise Exception("Failed to get calls")
    def clear_directory(self,dir_path):
        for filename in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, filename)
                    if os.path.isfile(file_path):
                            os.remove(file_path)
    def loader(self,time_from,current_time):
        access_token=SkorozvonLoader.get_access_token(self)['access_token']
        count=0
        flag=False
        df = DataFrame(
                columns=["Agent_Name", "Client_Number","Employee_Number","EmployeeId",
                        "Time_Started", "Time_Ended","Duration",
                        "RecordingID","Direction","Type","Reason"]
                        )
        call_data=SkorozvonLoader.get_calls_safely(self,access_token,time_from,current_time)['data']
        if call_data:
            for call in call_data:
                if call['recording_url']:
                        if call['duration']>30:
                            flag=True
                            recording=SkorozvonLoader.get_recording_safely(self,call['recording_url'],access_token)
                            with open(f"loader_factory/mp3/{count}.mp3", "wb") as f:
                                    f.write(recording.content)
                            audio_file=MP3(f"loader_factory/mp3/{count}.mp3")
                            duration=audio_file.info.length
                            if duration>30:
                                    flag=False
                                    employee_number=SkorozvonLoader.get_worker_safely(self,access_token,call['user']['id'])
                                    client_number=0
                                    reason=0
                                    if call['call_type_code']=='outgoing':
                                        client_number=call['phone']

                                    elif call['call_type_code']=='incoming':
                                        client_number=call['source']
                                    else:
                                        raise Exception("Unknown call type")
                                    if call['terminator']=='Оператор':
                                        reason="Сотрудник"
                                    else:
                                       reason="Клиент"
                                    ended_at=datetime.fromtimestamp((parser.parse(call['started_at']).timestamp())+call['duration'])
                                    df.loc[len(df)] = [call['user']['name'], client_number,employee_number,call['user']['id'],
                                                                            call['started_at'],ended_at,
                                                                            call['duration'],
                                                                            call['id'],call['call_type_code'],call['scenario_result']['name'],reason]
                                    count += 1
            if flag:
                os.remove(f"loader_factory/mp3/{count}.mp3")
            df.to_csv(f"loader_factory/csv/all.csv", encoding='utf-8')
            logging.info("Skorozvon ready")
        else:
             logging.info("Skorozvon empty")

    mp3_path = r"loader_factory/mp3"
    csv_path = r"loader_factory/csv"

    '''
    language = "ru"
    prompt_file_name = "prompt_file_bankruptcy.txt"
    checklist_file_name = "check_list_bankruptcy.json"
    '''
    def main(self, time_from):
        if time_from<0: raise Exception("Negative value")
        current_time=time.time()
        timer=0
        while True:
            try:
                timer+=120
                self.loader(time_from,current_time)
            except Exception as e:
                mp3_path = self.mp3_path
                csv_path = self.csv_path
                self.clear_directory(mp3_path)
                self.clear_directory(csv_path)
                logging.error('Skorozvon error:', str(e))
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
            "end_reason": results["Reason"][numb],
        }
        return sample_call_data

    def gettype(self, results, anal, numb):
        return results["Type"][numb]
if __name__ == '__main__':
    loader=SkorozvonLoader()
    loader.main(10000)