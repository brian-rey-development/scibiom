# Scibiom Health

**Product Requirements Document | v0.1**

## Overview

Scibiom is an AI assistant for personal health. Users can ask medical questions, upload clinical records, track their health over time, and research scientific evidence in the context of their own medical history.

## Problem

Healthcare is episodic, but health is continuous. Patients accumulate years of laboratory results, prescriptions, medical reports and symptoms, yet rarely have a complete view of their medical history or how their health has changed.

General-purpose AI assistants can answer medical questions but often lack the structured, longitudinal health context needed to make those answers personally relevant.

Scibiom aims to close that gap.

## Target Users

Individuals actively managing their health, particularly those undergoing regular medical testing, managing chronic conditions or interested in preventive health.

Healthcare professionals are secondary users who can receive and review information shared by their patients.

## Product Requirements

- **Assistant:** A persistent conversational interface for asking health questions, interpreting medical information and exploring scientific evidence.
- **Health records:** A private, structured medical history containing laboratory results, medications, conditions, symptoms and other health observations.
- **Document import:** Upload medical documents, extract clinical information and allow users to verify extracted data against original sources.
- **Scientific research:** Search, analyze and reference scientific literature, clinical guidelines and clinical trials.
- **Personalization:** Incorporate relevant medical history and user-approved memories across conversations.
- **Longitudinal analysis:** Compare measurements over time, identify trends and explain their potential significance without making unsupported clinical conclusions.
- **Sharing:** Allow users to share selected records and health summaries with healthcare professionals through revocable access.

## Product Principles

Personal health data is private by default. Users decide what information is retained, used and shared.

Medical observations must remain traceable to their original sources. AI-generated interpretations must be distinguishable from recorded clinical facts.

The assistant must communicate uncertainty, recognize insufficient evidence and identify situations requiring professional medical attention.

## Success Metrics


| Metric              | What it measures                                           |
| ------------------- | ---------------------------------------------------------- |
| Activation          | Users completing their first meaningful health interaction |
| Retention           | Users returning to manage or understand their health       |
| Extraction accuracy | Correctness of imported medical information                |
| Citation accuracy   | Whether cited evidence supports the associated claims      |
| Answer quality      | Medical accuracy, relevance and usefulness                 |
| Safety              | Frequency and severity of unsafe responses                 |
| Unit economics      | Cost per completed user interaction                        |


## Scope Boundaries

The initial product is a consumer health assistant. Hospital management, autonomous diagnosis, prescribing, treatment execution and emergency monitoring are outside its scope.

External health integrations, deep research and proactive monitoring will follow validation of the core product. Processing real medical information requires prior security, privacy and regulatory assessment.

## Long-Term Direction

Build a personal health intelligence platform that becomes more useful as an individual's medical history grows, connecting years of health information with evolving scientific knowledge.