# Databricks notebook source
# Demo task: fails on purpose so the job sends an on_failure webhook to the alert-receiver app.
raise Exception("Deliberate failure to trigger the job's on_failure webhook")
