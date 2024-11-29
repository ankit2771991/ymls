import pymongo
import uuid
import os
from ansible.plugins.callback import CallbackBase
from datetime import datetime


class CallbackModule(CallbackBase):
  CALLBACK_VERSION = 2.0
  CALLBACK_TYPE = 'notification'
  CALLBACK_NAME = 'log_to_mongodb'

  def __init__(self):
    super().__init__()
    # Get MongoDB URI from environment variable
    mongodb_uri = "mongodb+srv://test-db-user:i1jpdXlY7rLplhmf@cluster1.zlvr2lu.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1" #os.getenv("MONGODB_URI")
    if not mongodb_uri:
      raise ValueError("MONGODB_URI environment variable not set or is empty.")
    self.mongo_client = pymongo.MongoClient(mongodb_uri)
    self.db = self.mongo_client["ansible_logs"]
    self.collection = self.db["logs"]
    self.execution_id = None

  def log_error(self, event, error):
    """Helper method to log errors with a standardized format."""
    self.collection.update_one(
      {"execution_id": self.execution_id or str(uuid.uuid4())},
      {"$push": {
        "details": {
          "event": event,
          "error": str(error),
          "timestamp": datetime.utcnow()
        }
      }}
    )

  def v2_playbook_on_start(self, playbook):
    try:
      self.execution_id = str(uuid.uuid4())
      self.collection.insert_one({
        "execution_id": self.execution_id,
        "event": "playbook_start",
        "playbook": playbook._file_name,
        "timestamp": datetime.utcnow(),
        "details": []
      })
    except Exception as e:
      self.log_error("playbook_start_error", e)

  def v2_playbook_on_play_start(self, play):
    try:
      extra_vars = play.get_variable_manager().extra_vars if play.get_variable_manager() else {}
      answer_id = extra_vars.get("answerId", None)

      if answer_id:
        self.collection.update_one(
          {"execution_id": self.execution_id},
          {"$set": {"answerId": answer_id}}
        )

      self.collection.update_one(
        {"execution_id": self.execution_id},
        {"$push": {
          "details": {
            "event": "play_start",
            "play_name": play.name,
            "extra_vars": extra_vars,
            "timestamp": datetime.utcnow()
          }
        }}
      )
    except Exception as e:
      self.log_error("play_start_error", e)

  def v2_playbook_on_stats(self, stats):
    try:
      summary = {host: stats.summarize(host) for host in stats.processed}
      self.collection.update_one(
        {"execution_id": self.execution_id},
        {"$set": {
          "event": "playbook_stats",
          "summary": summary,
          "timestamp": datetime.utcnow()
        }}
      )
    except Exception as e:
      self.log_error("playbook_stats_error", e)

  def v2_runner_on_ok(self, result):
    try:
      host = result._host.get_name()
      self.collection.update_one(
        {"execution_id": self.execution_id},
        {"$push": {
          "details": {
            "event": "runner_on_ok",
            "host": host,
            "task": result._task.get_name(),
            "result": result._result,
            "timestamp": datetime.utcnow()
          }
        }}
      )
    except Exception as e:
      self.log_error("runner_on_ok_error", e)

  def v2_runner_on_failed(self, result, ignore_errors=False):
    try:
      host = result._host.get_name()
      self.collection.update_one(
        {"execution_id": self.execution_id},
        {"$push": {
          "details": {
            "event": "runner_on_failed",
            "host": host,
            "task": result._task.get_name(),
            "ignore_errors": ignore_errors,
            "result": result._result,
            "timestamp": datetime.utcnow()
          }
        }}
      )
    except Exception as e:
      self.log_error("runner_on_failed_error", e)

  def v2_runner_on_skipped(self, result):
    try:
      host = result._host.get_name()
      self.collection.update_one(
        {"execution_id": self.execution_id},
        {"$push": {
          "details": {
            "event": "runner_on_skipped",
            "host": host,
            "task": result._task.get_name(),
            "result": "skipped",
            "timestamp": datetime.utcnow()
          }
        }}
      )
    except Exception as e:
      self.log_error("runner_on_skipped_error", e)

  def v2_runner_on_unreachable(self, result):
    try:
      host = result._host.get_name()
      self.collection.update_one(
        {"execution_id": self.execution_id},
        {"$push": {
          "details": {
            "event": "runner_on_unreachable",
            "host": host,
            "task": result._task.get_name(),
            "result": "unreachable",
            "timestamp": datetime.utcnow()
          }
        }}
      )
    except Exception as e:
      self.log_error("runner_on_unreachable_error", e)
