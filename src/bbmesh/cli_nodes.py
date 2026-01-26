#!/usr/bin/env python3
"""
BBMesh Node Management CLI Tool

Command-line interface for managing tracked nodes and admin registrations.
"""

import click
from pathlib import Path
from datetime import datetime
from typing import Optional

from bbmesh.core.node_tracker import NodeTracker
from bbmesh.core.admin_manager import AdminManager


@click.group()
@click.option('--db', default='data/bbmesh.db', help='Database path')
@click.pass_context
def cli(ctx, db):
    """BBMesh Node Management Tool
    
    Manage tracked mesh nodes and admin registrations.
    """
    ctx.ensure_object(dict)
    ctx.obj['db_path'] = db


@cli.command()
@click.option('--limit', default=None, type=int, help='Limit number of results')
@click.pass_context
def list(ctx, limit):
    """List all tracked nodes"""
    try:
        tracker = NodeTracker(ctx.obj['db_path'])
        nodes = tracker.get_all_nodes(limit=limit)
        
        if not nodes:
            click.echo("No nodes tracked yet.")
            return
        
        # Print header
        click.echo(f"\n{'Node ID':<15} {'Name':<20} {'First Seen':<20} {'Last Seen':<20} {'Messages':<10}")
        click.echo("-" * 90)
        
        # Print nodes
        for node in nodes:
            first_seen = node['first_seen_at'][:19] if node['first_seen_at'] else 'N/A'
            last_seen = node['last_seen_at'][:19] if node['last_seen_at'] else 'N/A'
            
            click.echo(
                f"{node['node_id']:<15} "
                f"{node['node_name']:<20} "
                f"{first_seen:<20} "
                f"{last_seen:<20} "
                f"{node['message_count']:<10}"
            )
        
        # Print statistics
        stats = tracker.get_statistics()
        click.echo(f"\nTotal: {stats['total_nodes']} nodes | "
                  f"Active: {stats['active_nodes']} | "
                  f"Inactive: {stats['inactive_nodes']} | "
                  f"Messages: {stats['total_messages']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('node_id')
@click.pass_context
def info(ctx, node_id):
    """Show detailed information about a specific node"""
    try:
        tracker = NodeTracker(ctx.obj['db_path'])
        node = tracker.get_node_info(node_id)
        
        if not node:
            click.echo(f"Node {node_id} not found.")
            return
        
        click.echo(f"\nNode Information:")
        click.echo(f"  Node ID:       {node['node_id']}")
        click.echo(f"  Name:          {node['node_name']}")
        click.echo(f"  First Seen:    {node['first_seen_at']}")
        click.echo(f"  Last Seen:     {node['last_seen_at']}")
        click.echo(f"  Message Count: {node['message_count']}")
        click.echo(f"  Created:       {node['created_at']}")
        click.echo(f"  Updated:       {node['updated_at']}")
        
        # Calculate days since last seen
        last_seen = datetime.fromisoformat(node['last_seen_at'])
        days_ago = (datetime.now() - last_seen).days
        click.echo(f"  Days Inactive: {days_ago}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('node_id')
@click.pass_context
def reset(ctx, node_id):
    """Reset a node's tracking (mark as new)
    
    This will cause the node to trigger a "new node" notification
    on its next message.
    """
    try:
        tracker = NodeTracker(ctx.obj['db_path'])
        
        if tracker.reset_node(node_id):
            click.echo(f"✅ Reset node {node_id}")
            click.echo("   Node will be treated as new on next message.")
        else:
            click.echo(f"❌ Node {node_id} not found")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--days', default=90, help='Remove nodes not seen in X days')
@click.confirmation_option(prompt='Are you sure you want to clear old nodes?')
@click.pass_context
def clear(ctx, days):
    """Clear nodes not seen in X days
    
    Permanently removes nodes from the database that haven't
    been active in the specified number of days.
    """
    try:
        tracker = NodeTracker(ctx.obj['db_path'])
        count = tracker.clear_old_nodes(days)
        
        if count > 0:
            click.echo(f"✅ Removed {count} nodes not seen in {days} days")
        else:
            click.echo(f"No nodes found older than {days} days")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def stats(ctx):
    """Show node tracking statistics"""
    try:
        tracker = NodeTracker(ctx.obj['db_path'])
        stats = tracker.get_statistics()
        
        click.echo("\nNode Tracking Statistics:")
        click.echo(f"  Total Nodes:    {stats['total_nodes']}")
        click.echo(f"  Active Nodes:   {stats['active_nodes']} (seen in last {stats['threshold_days']} days)")
        click.echo(f"  Inactive Nodes: {stats['inactive_nodes']}")
        click.echo(f"  Total Messages: {stats['total_messages']}")
        
        if stats['total_nodes'] > 0:
            avg_messages = stats['total_messages'] / stats['total_nodes']
            click.echo(f"  Avg Messages:   {avg_messages:.1f} per node")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.pass_context
def admins(ctx):
    """List registered admin nodes"""
    try:
        # Create minimal config for AdminManager
        config = {
            'notification_format': '🆕 {node_name} ({node_id})',
            'admin_psk': None,
            'psk_enabled': False,
            'admin_nodes': []
        }
        manager = AdminManager(ctx.obj['db_path'], config, None)
        admins = manager.get_active_admins()
        
        if not admins:
            click.echo("No admin nodes registered.")
            return
        
        # Print header
        click.echo(f"\n{'Node ID':<15} {'Name':<20} {'Method':<10} {'Registered':<20}")
        click.echo("-" * 70)
        
        # Print admins
        for admin in admins:
            registered = admin['registered_at'][:19] if admin['registered_at'] else 'N/A'
            
            click.echo(
                f"{admin['node_id']:<15} "
                f"{admin['node_name']:<20} "
                f"{admin['registration_method']:<10} "
                f"{registered:<20}"
            )
        
        # Print count
        counts = manager.get_admin_count()
        click.echo(f"\nTotal: {counts['total']} admins | "
                  f"Active: {counts['active']} | "
                  f"Inactive: {counts['inactive']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('node_id')
@click.pass_context
def deactivate_admin(ctx, node_id):
    """Deactivate an admin node"""
    try:
        config = {
            'notification_format': '🆕 {node_name} ({node_id})',
            'admin_psk': None,
            'psk_enabled': False,
            'admin_nodes': []
        }
        manager = AdminManager(ctx.obj['db_path'], config, None)
        
        if manager.deactivate_admin(node_id):
            click.echo(f"✅ Deactivated admin {node_id}")
        else:
            click.echo(f"❌ Admin {node_id} not found")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('node_id')
@click.pass_context
def activate_admin(ctx, node_id):
    """Activate an admin node"""
    try:
        config = {
            'notification_format': '🆕 {node_name} ({node_id})',
            'admin_psk': None,
            'psk_enabled': False,
            'admin_nodes': []
        }
        manager = AdminManager(ctx.obj['db_path'], config, None)
        
        if manager.activate_admin(node_id):
            click.echo(f"✅ Activated admin {node_id}")
        else:
            click.echo(f"❌ Admin {node_id} not found")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument('node_id')
@click.confirmation_option(prompt='Are you sure you want to remove this admin?')
@click.pass_context
def remove_admin(ctx, node_id):
    """Remove an admin node from database"""
    try:
        config = {
            'notification_format': '🆕 {node_name} ({node_id})',
            'admin_psk': None,
            'psk_enabled': False,
            'admin_nodes': []
        }
        manager = AdminManager(ctx.obj['db_path'], config, None)
        
        if manager.remove_admin(node_id):
            click.echo(f"✅ Removed admin {node_id}")
        else:
            click.echo(f"❌ Admin {node_id} not found")
            
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    cli()

# Made with Bob
