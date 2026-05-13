#!/usr/bin/env python3
"""
============================================================================
PIPELINE — Universal Input Pipeline Orchestrator
============================================================================
Orquesta el flujo completo del arnés para cualquier input:
INGEST → ANALYZE → DECIDE → ACT → LOG → VERIFY

Usage (from agent):
    from harness.pipeline import Pipeline
    pipe = Pipeline()
    result = pipe.run(input_text)

Or from CLI:
    python pipeline.py <input> [--type youtube|text|file|url]
============================================================================
"""

import os
import sys
import json
import uuid
from datetime import datetime
from typing import Optional

# Ensure we can import sibling modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from harness.harness_db import HarnessDB
from harness.ingest import ingest, detect_input_type


SESSION_ID = None  # Set once per pipeline run


class Pipeline:
    """
    Universal input pipeline.
    
    Each stage is a method so the agent can override or inspect any step.
    """
    
    def __init__(self, agent_name: str = "Hermes Agent"):
        self.db = HarnessDB()
        self.agent_name = agent_name
        self.session_id = f"pipe-{uuid.uuid4().hex[:12]}"
        self.context_usage_pct = 10  # Starting estimate
        
    # ------------------------------------------------------------------
    # STAGE 1: INGEST
    # ------------------------------------------------------------------
    def stage_ingest(self, raw_input: str, input_type: Optional[str] = None) -> dict:
        """
        Detect input type and extract structured content.
        Returns content dict with 'type', 'content', 'metadata', etc.
        """
        print(f"  ⬇️ INGEST: detecting input type...")
        result = ingest(raw_input, input_type)
        source = result['type']
        meta = result['metadata']
        
        if source == 'youtube':
            print(f"     YouTube: {meta.get('title', 'unknown')}")
            print(f"     Channel: {meta.get('channel', 'unknown')}")
            print(f"     Language: {meta.get('language', 'unknown')}")
            print(f"     Segments: {meta.get('segment_count', 0)}")
        elif source == 'file':
            print(f"     File: {meta.get('filename', 'unknown')}")
        elif source == 'url':
            print(f"     URL: {meta.get('url', 'unknown')}")
        
        print(f"     Content length: {len(result['content'])} chars")
        return result
    
    # ------------------------------------------------------------------
    # STAGE 2: ANALYZE
    # ------------------------------------------------------------------
    def stage_analyze(self, ingested: dict) -> dict:
        """
        Analyze the ingested content and produce a structured analysis.
        This stage extracts: topics, key points, entities, urgency, action items.
        
        The analysis dict is later used by stage_decide to determine actions.
        """
        source_type = ingested['type']
        content = ingested['content']
        meta = ingested['metadata']
        
        analysis = {
            'source_type': source_type,
            'content_length': len(content),
            'topics': [],
            'key_points': [],
            'urgency': 'normal',       # low, normal, high, critical
            'suggested_actions': [],    # hints for stage_decide
        }
        
        if source_type == 'youtube':
            analysis['topics'].append('video_tutorial')
            analysis['key_points'].append(f"Video: {meta.get('title', 'unknown')}")
            analysis['key_points'].append(f"By: {meta.get('channel', 'unknown')}")
            analysis['key_points'].append(f"Language: {meta.get('language', 'unknown')}")
        
        elif source_type == 'file':
            analysis['topics'].append('document')
            analysis['key_points'].append(f"File: {meta.get('filename', 'unknown')}")
        
        elif source_type == 'text':
            analysis['topics'].append('message')
        
        # The LLM (agent) will enrich this analysis with deeper reasoning
        # in the decide stage. This provides the structural skeleton.
        
        return analysis
    
    # ------------------------------------------------------------------
    # STAGE 3: DECIDE
    # ------------------------------------------------------------------
    def stage_decide(self, analysis: dict) -> dict:
        """
        Determine what actions to take based on the analysis.
        
        Returns a decision dict with:
        - actions: list of action dicts {type, params}
        - create_tasks: list of task dicts to create in DB
        - log_decision: bool
        - update_spec: optional spec data
        """
        decision = {
            'actions': [],
            'create_tasks': [],
            'log_decision': True,
            'update_spec': None,
        }
        
        # Structural decisions based on content type
        # The LLM will override these with deeper reasoning
        source_type = analysis['source_type']
        
        if source_type == 'youtube':
            decision['actions'].append({
                'type': 'analyze_content',
                'description': f"Analyze video content: {analysis.get('key_points', [''])[0] if analysis.get('key_points') else 'unknown'}",
            })
        
        decision['actions'].append({
            'type': 'log_to_db',
            'description': 'Log pipeline execution to harness.db',
        })
        
        return decision
    
    # ------------------------------------------------------------------
    # STAGE 4: ACT
    # ------------------------------------------------------------------
    def stage_act(self, decision: dict, ingested: dict, analysis: dict) -> dict:
        """
        Execute the decided actions.
        Returns results dict with outcomes of each action.
        """
        results = {'actions_taken': [], 'tasks_created': [], 'errors': []}
        
        for action in decision['actions']:
            action_type = action.get('type')
            try:
                if action_type == 'log_to_db':
                    results['actions_taken'].append({
                        'type': 'log_to_db',
                        'status': 'delegated_to_agent',
                    })
                
                elif action_type == 'create_task':
                    # Create task in DB
                    task_id = self.db.create_task(
                        code=action.get('code', 'TASK-' + uuid.uuid4().hex[:6]),
                        title=action.get('title', 'Unnamed task'),
                        epic_id=action.get('epic_id'),
                        description=action.get('description', ''),
                        acceptance_criteria=action.get('criteria', []),
                        priority=action.get('priority', 5),
                        tags=action.get('tags', []),
                    )
                    results['actions_taken'].append({
                        'type': 'create_task',
                        'task_id': task_id,
                        'code': action.get('code', ''),
                        'status': 'created',
                    })
                
                elif action_type == 'create_spec':
                    spec_id = self.db.create_spec(
                        task_id=action['task_id'],
                        title=action['title'],
                        content=action['content'],
                        sdd_level=action.get('sdd_level', 2),
                        generated_files=action.get('generated_files', []),
                    )
                    results['actions_taken'].append({
                        'type': 'create_spec',
                        'spec_id': spec_id,
                        'status': 'created',
                    })
                
                elif action_type == 'log_decision':
                    self.db.log_decision(
                        task_id=action.get('task_id'),
                        title=action.get('title', 'Decision'),
                        context=action.get('context', ''),
                        options=action.get('options', []),
                        chosen=action.get('chosen', ''),
                        rationale=action.get('rationale', ''),
                        decided_by=self.agent_name,
                    )
                    results['actions_taken'].append({
                        'type': 'log_decision',
                        'status': 'logged',
                    })
                
                elif action_type == 'analyze_content':
                    # Content analysis is done by the LLM agent, not this script
                    results['actions_taken'].append({
                        'type': 'analyze_content',
                        'status': 'delegated_to_agent',
                    })
                
                else:
                    results['actions_taken'].append({
                        'type': action_type,
                        'status': 'unknown_action_type',
                    })
            
            except Exception as e:
                results['errors'].append({
                    'action': action_type,
                    'error': str(e),
                })
        
        return results
    
    # ------------------------------------------------------------------
    # STAGE 5: LOG
    # ------------------------------------------------------------------
    def stage_log(self, ingested: dict, analysis: dict, decision: dict,
                  results: dict) -> str:
        """
        Persist the entire pipeline execution to harness.db.
        Creates agent_logs entry and closes the session.
        """
        # Build a comprehensive summary
        source_type = ingested['type']
        meta = ingested['metadata']
        
        if source_type == 'youtube':
            summary_parts = [
                f"Pipeline: ingested YouTube video '{meta.get('title', 'unknown')}'",
                f"by {meta.get('channel', 'unknown')} ({meta.get('language', 'unknown')})",
            ]
        elif source_type == 'file':
            summary_parts = [
                f"Pipeline: ingested file '{meta.get('filename', 'unknown')}'",
            ]
        elif source_type == 'text':
            preview = ingested['content'][:80].replace('\n', ' ')
            summary_parts = [
                f"Pipeline: ingested text message",
                f"preview: '{preview}...'",
            ]
        else:
            summary_parts = [f"Pipeline: ingested {source_type}"]
        
        # Add action results
        actions_done = [a['type'] for a in results.get('actions_taken', [])]
        if actions_done:
            summary_parts.append(f"actions: {', '.join(actions_done)}")
        
        errors = results.get('errors', [])
        if errors:
            summary_parts.append(f"errors: {len(errors)}")
        
        summary = ' | '.join(summary_parts)
        
        # Log to agent_logs
        self.db.log_activity(
            session_id=self.session_id,
            agent_name=self.agent_name,
            task_id=None,  # General pipeline run, not tied to a single task
            action="pipeline_run",
            summary=summary,
            files_changed=None,
            context_usage_pct=self.context_usage_pct,
            tokens_used=0,
            status="completed" if not errors else "failed",
            error_message=str(errors[0]['error']) if errors else None,
        )
        
        # Close session
        self.db.close_session(
            self.session_id,
            summary=summary,
            context_usage_end=self.context_usage_pct + 5,
        )
        
        return self.session_id
    
    # ------------------------------------------------------------------
    # STAGE 6: VERIFY
    # ------------------------------------------------------------------
    def stage_verify(self) -> dict:
        """
        Verify environment consistency after pipeline execution.
        """
        try:
            summary = self.db.get_project_summary()
            return {
                'status': 'ok',
                'tasks_total': summary['tasks']['total'],
                'tasks_done': summary['tasks']['done'],
                'tasks_pending': summary['tasks']['pending'],
                'recent_activity': summary['recent_activity'][:200],
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
            }
    
    # ------------------------------------------------------------------
    # FULL PIPELINE RUN
    # ------------------------------------------------------------------
    def run(self, raw_input: str, input_type: Optional[str] = None) -> dict:
        """
        Execute the full pipeline for any input.
        
        Returns a comprehensive result dict with all stages.
        """
        print(f"\n{'='*60}")
        print(f"  PIPELINE RUN — {self.session_id}")
        print(f"{'='*60}")
        
        # Open session
        self.db.open_session(self.session_id, self.agent_name,
                            context_usage_start=self.context_usage_pct)
        
        # Stage 1: INGEST
        print(f"\n📥 Stage 1/6: INGEST")
        ingested = self.stage_ingest(raw_input, input_type)
        
        # Stage 2: ANALYZE
        print(f"\n🔍 Stage 2/6: ANALYZE")
        analysis = self.stage_analyze(ingested)
        
        # Stage 3: DECIDE
        print(f"\n🧠 Stage 3/6: DECIDE")
        decision = self.stage_decide(analysis)
        print(f"     Actions planned: {len(decision['actions'])}")
        for a in decision['actions']:
            print(f"       - {a['type']}: {a.get('description', '')}")
        
        # Stage 4: ACT
        print(f"\n⚡ Stage 4/6: ACT")
        results = self.stage_act(decision, ingested, analysis)
        print(f"     Actions taken: {len(results['actions_taken'])}")
        if results['errors']:
            print(f"     Errors: {len(results['errors'])}")
        
        # Stage 5: LOG
        print(f"\n💾 Stage 5/6: LOG")
        session = self.stage_log(ingested, analysis, decision, results)
        print(f"     Session: {session}")
        
        # Stage 6: VERIFY
        print(f"\n✅ Stage 6/6: VERIFY")
        verification = self.stage_verify()
        print(f"     Status: {verification['status']}")
        if 'tasks_total' in verification:
            print(f"     DB: {verification['tasks_done']}/{verification['tasks_total']} tasks done")
        
        print(f"\n{'='*60}")
        print(f"  PIPELINE COMPLETE ✓")
        print(f"{'='*60}")
        
        return {
            'session_id': self.session_id,
            'ingested': ingested,
            'analysis': analysis,
            'decision': decision,
            'results': results,
            'verification': verification,
        }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <input> [--type youtube|text|file|url]")
        print()
        print("Runs the full pipeline autonomously (INGEST only, DECIDE is delegated to agent).")
        sys.exit(1)
    
    input_text = sys.argv[1]
    input_type = None
    if '--type' in sys.argv:
        idx = sys.argv.index('--type')
        if idx + 1 < len(sys.argv):
            input_type = sys.argv[idx + 1]
    
    pipe = Pipeline()
    result = pipe.run(input_text, input_type)
    
    # Print structured summary
    print(f"\n📋 Pipeline Result Summary:")
    i = result['ingested']
    print(f"  Input type: {i['type']}")
    if i['type'] == 'youtube':
        print(f"  Video: {i['metadata'].get('title', 'N/A')}")
    print(f"  Content: {len(i['content'])} chars")
    print(f"  Session: {result['session_id']}")
    
    v = result['verification']
    if v['status'] == 'ok':
        print(f"  Verification: ✅ OK")
