import grpc
import callcenter_pb2
import callcenter_pb2_grpc
import time
import uuid

def generate_audio_chunks(call_id, duration=5):
    """Генератор тестовых аудио-чанков"""
    for i in range(duration):
        # Эмуляция аудио данных
        audio_data = f"audio_chunk_{i}".encode()
        
        yield callcenter_pb2.AudioChunk(
            audio_data=audio_data,
            call_id=call_id,
            sample_rate=44100,
            channels=1,
            codec="pcm"
        )
        print(f"Отправлен аудио-чанк {i}")
        time.sleep(1)  # Пауза между чанками

def run_call():
    """Запуск тестового звонка"""
    try:
        channel = grpc.insecure_channel('localhost:50051')
        stub = callcenter_pb2_grpc.CallCenterStub(channel)
        
        call_id = str(uuid.uuid4())
        print(f"Начало звонка с ID: {call_id}")
        
        # Создаем поток запросов
        request_stream = generate_audio_chunks(call_id, duration=5)
        
        # Отправляем запрос и получаем ответы
        responses = stub.LiveCall(request_stream)
        
        # Обрабатываем ответы от сервера
        for i, response in enumerate(responses):
            print(f"Получен ответ {i}: {response.audio_data.decode()}")
            
    except grpc.RpcError as e:
        print(f"Ошибка RPC: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"Общая ошибка: {e}")
    finally:
        print("Звонок завершен")

if __name__ == '__main__':
    run_call()