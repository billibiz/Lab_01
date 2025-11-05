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