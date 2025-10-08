# Лабораторная работа 01. Реализация RPC-сервиса с использованием gRPC
#### Выполнила: Хлебова Екатерина Максимовна, группа АБП-231
# Цель работы:

- освоить принципы удаленного вызова процедур (RPC) и их применение
в распределенных системах;
- изучить основы фреймворка gRPC и языка определения интерфейсов
Protocol Buffers (Protobuf);
- научиться определять сервисы и сообщения с помощью Protobuf;
- реализовать клиент-серверное приложение на языке Python с
использованием gRPC;
- получить практические навыки в генерации кода, реализации серверной
логики и клиентских вызовов для различных типов RPC.
## Задача:
Необходимо разработать распределенную систему "Колл-центр", состоящую из сервера и клиента. Клиент (оператор) должен иметь возможность установить голосовое соединение с сервером (абонентом) и в реальном времени передавать аудиоданные, а также получать ответные аудиоданные.
## Стек программного обеспечения:
- Операционная система: Ubuntu 20.04.6 LTS
- Язык программирования: Python 3.8+.
- Среда изоляции зависимостей:
  - venv – стандартный модуль Python для создания легковесных
виртуальных окружений.
- Ключевые библиотеки и фреймворки:
  - grpcio. Основная библиотека, содержащая реализацию gRPC для
Python, необходимая для запуска клиента и сервера.
  - grpcio-tools.Инструментарий, включающий компилятор Protocol
Buffers (protoc) для автоматической генерации Python-кода
из .proto файлов.

## Вариант № 20. Колл-центр

Сервис CallCenter: метод LiveCall(stream
AudioChunk) для двунаправленной передачи
аудио в реальном времени (Bidirectional
streaming RPC).

### 1. Настройка рабочего окружения
Обновление пакетов и установка Python/pip
```
sudo apt update
sudo apt install python3 python3-pip python3-venv
```
![Скриншот 24-09-2025 100423](https://github.com/user-attachments/assets/55ba601a-6de8-42ad-9bba-bdb81167dfc8)

![Скриншот 24-09-2025 100630](https://github.com/user-attachments/assets/9be03b2e-caef-4f82-81ba-2577959f0435)

Создание виртуального окружения
```
python3 -m venv grpc_callcenter_venv
source grpc_callcenter_venv/bin/activate
```
![Скриншот 24-09-2025 101548](https://github.com/user-attachments/assets/15539eb9-afcd-4360-82ed-fb681741be3b)


Установка необходимых библиотек
```
pip install grpcio grpcio-tools
```


### 2. Создание .proto файла (callcenter.proto)
```
syntax = "proto3";

package callcenter;

service CallCenter {
  rpc LiveCall(stream AudioChunk) returns (stream AudioChunk);
}

message AudioChunk {
  bytes audio_data = 1;
  string call_id = 2;
  int32 sample_rate = 3;
  int32 channels = 4;
  string codec = 5;
}
```
![Скриншот 24-09-2025 101757](https://github.com/user-attachments/assets/15163eeb-b5b0-4a89-9339-a6486e0815bc)

### 3. Генерация Python-кода из .proto файла
```
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. callcenter.proto
```
### 4. Реализация серверной части (server.py)
```
import grpc
import callcenter_pb2
import callcenter_pb2_grpc
import threading
import queue
import time
from concurrent import futures

class CallCenterServicer(callcenter_pb2_grpc.CallCenterServicer):
    def __init__(self):
        self.active_calls = {}
        self.lock = threading.Lock()
        
    def LiveCall(self, request_iterator, context):
        """Bidirectional streaming RPC для обработки аудио звонков"""
        print("Новое подключение к LiveCall установлено")
        
        call_id = None
        audio_queue = queue.Queue()
        
        def receive_messages():
            nonlocal call_id
            try:
                for audio_chunk in request_iterator:
                    if not call_id:
                        call_id = audio_chunk.call_id
                        with self.lock:
                            self.active_calls[call_id] = audio_queue
                        print(f"Начат звонок с ID: {call_id}")
                    
                    print(f"Получен аудио-чанк от {call_id}, размер: {len(audio_chunk.audio_data)} байт")
                    
                    # Обработка аудио (эмуляция)
                    processed_audio = self.process_audio(audio_chunk)
                    audio_queue.put(processed_audio)
                    
            except Exception as e:
                print(f"Ошибка при приеме аудио: {e}")
            finally:
                # Очистка при завершении звонка
                if call_id:
                    with self.lock:
                        if call_id in self.active_calls:
                            del self.active_calls[call_id]
                    print(f"Звонок {call_id} завершен")
        
        # Запуск потока для приема сообщений
        receiver_thread = threading.Thread(target=receive_messages)
        receiver_thread.daemon = True
        receiver_thread.start()
        
        # Отправка обработанных сообщений обратно клиенту
        try:
            while context.is_active():
                try:
                    # Ждем следующее сообщение для отправки
                    response = audio_queue.get(timeout=0.5)
                    yield response
                except queue.Empty:
                    # Проверяем, активен ли еще контекст
                    if not context.is_active():
                        break
                    continue
                except Exception as e:
                    print(f"Ошибка в основном цикле: {e}")
                    break
        except Exception as e:
            print(f"Ошибка при отправке аудио: {e}")
        finally:
            print("Поток отправки завершен")
    
    def process_audio(self, audio_chunk):
        """Эмуляция обработки аудио"""
        timestamp = f"|processed_{time.time()}|".encode()
        processed_data = audio_chunk.audio_data + timestamp
        
        return callcenter_pb2.AudioChunk(
            audio_data=processed_data,
            call_id=audio_chunk.call_id,
            sample_rate=audio_chunk.sample_rate,
            channels=audio_chunk.channels,
            codec=audio_chunk.codec
        )

def serve():
    # Создаем сервер с ThreadPoolExecutor
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    callcenter_pb2_grpc.add_CallCenterServicer_to_server(
        CallCenterServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Сервер CallCenter запущен на порту 50051")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Остановка сервера...")
        server.stop(0)

if __name__ == '__main__':
    serve()
```

### 5. Реализация клиентской части (client.py)
```
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
```
![Скриншот 24-09-2025 103850](https://github.com/user-attachments/assets/91e6802f-1c29-4369-bce7-01de25cc0e08)

### 6. Запуск и тестирование
Терминал 1 (Сервер):
```
source grpc_callcenter_venv/bin/activate
python server.py
```
Терминал 2 (Клиент):
```
source grpc_callcenter_venv/bin/activate
python client.py
```
![Скриншот 24-09-2025 103850](https://github.com/user-attachments/assets/85d5bc4a-d46e-4261-bdde-3529e257e6dd)

# Вывод работы
В ходе работы успешно реализован RPC-сервис колл-центра с использованием gRPC. Реализован двунаправленный потоковый метод LiveCall для передачи аудио в реальном времени. Сервис корректно обрабатывает одновременные подключения, обеспечивает стабильную передачу данных и демонстрирует эффективность gRPC для задач потоковой передачи в режиме реального времени.
