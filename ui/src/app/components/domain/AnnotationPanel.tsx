/**
 * AnnotationPanel - Add context notes to events, decisions, trades
 * Critical for preserving operator knowledge
 * Now with full card UI, edit/delete functionality
 */

import { useState } from 'react';
import { Card } from '../primitives/Card';
import { Timestamp } from '../primitives/Timestamp';
import { Pencil, Trash2, Save, X } from 'lucide-react';

interface Annotation {
  id: string;
  linkedTo: {
    type: 'EVENT' | 'DECISION' | 'TRADE';
    id: string;
  };
  text: string;
  author: string;
  timestamp: string;
  tags?: string[];
}

interface AnnotationPanelProps {
  annotations: Annotation[];
  onAdd?: (annotation: Omit<Annotation, 'id' | 'timestamp'>) => void;
  onEdit?: (id: string, annotation: Omit<Annotation, 'id' | 'timestamp'>) => void;
  onDelete?: (id: string) => void;
  linkedContext?: {
    type: 'EVENT' | 'DECISION' | 'TRADE';
    id: string;
  };
  className?: string;
}

export function AnnotationPanel({ 
  annotations, 
  onAdd, 
  onEdit,
  onDelete,
  linkedContext, 
  className = '' 
}: AnnotationPanelProps) {
  const [isAdding, setIsAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [tags, setTags] = useState('');

  const handleSubmit = () => {
    if (!noteText.trim() || !linkedContext || !onAdd) return;

    onAdd({
      linkedTo: linkedContext,
      text: noteText.trim(),
      author: 'Current Operator', // Would come from auth context
      tags: tags.split(',').map(t => t.trim()).filter(Boolean)
    });

    setNoteText('');
    setTags('');
    setIsAdding(false);
  };

  const handleEdit = (annotation: Annotation) => {
    setEditingId(annotation.id);
    setNoteText(annotation.text);
    setTags(annotation.tags?.join(', ') || '');
  };

  const handleSaveEdit = (annotation: Annotation) => {
    if (!noteText.trim() || !onEdit) return;

    onEdit(annotation.id, {
      linkedTo: annotation.linkedTo,
      text: noteText.trim(),
      author: annotation.author,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean)
    });

    setEditingId(null);
    setNoteText('');
    setTags('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setNoteText('');
    setTags('');
  };

  const handleDelete = (id: string) => {
    if (onDelete && confirm('Delete this annotation? This cannot be undone.')) {
      onDelete(id);
    }
  };

  return (
    <Card className={className}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[var(--text-0)] uppercase tracking-wide">
          Annotations
        </h3>
        {!isAdding && (
          <button
            onClick={() => setIsAdding(true)}
            className="px-4 py-2 text-sm font-medium bg-[var(--accent)] text-white rounded hover:bg-[var(--accent-muted)] transition-colors"
          >
            + Add Note
          </button>
        )}
      </div>

      {/* Add Form - Full Card */}
      {isAdding && linkedContext && (
        <Card variant="outlined" className="mb-4 border-2 border-[var(--accent)]">
          <div className="mb-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-semibold text-[var(--text-0)]">New Annotation</h4>
              <button
                onClick={() => {
                  setIsAdding(false);
                  setNoteText('');
                  setTags('');
                }}
                className="p-1 text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors"
                title="Cancel"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="text-xs text-[var(--text-2)]">
              Annotating <span className="font-mono text-[var(--accent)]">{linkedContext.type}:{linkedContext.id}</span>
            </div>
          </div>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-[var(--text-1)] mb-2">
                Note Text
              </label>
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="Add your observation, context, or reasoning..."
                className="w-full px-3 py-3 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)] resize-none focus:outline-none focus:border-[var(--accent)] transition-colors"
                rows={4}
                autoFocus
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--text-1)] mb-2">
                Tags (optional)
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="e.g., critical, review, question"
                className="w-full px-3 py-2 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)] focus:outline-none focus:border-[var(--accent)] transition-colors"
              />
              <p className="text-xs text-[var(--text-2)] mt-1">Separate multiple tags with commas</p>
            </div>

            <button
              onClick={handleSubmit}
              disabled={!noteText.trim()}
              className="w-full px-4 py-3 text-sm font-medium bg-[var(--good)] text-white rounded hover:bg-[var(--good-muted)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              Save Annotation
            </button>
          </div>
        </Card>
      )}

      {/* Annotations List */}
      <div className="space-y-3">
        {annotations.length === 0 ? (
          <div className="text-center py-8 text-sm text-[var(--text-2)]">
            No annotations yet. Click "Add Note" to create your first annotation.
          </div>
        ) : (
          annotations.map((annotation) => {
            const isEditing = editingId === annotation.id;

            return (
              <Card key={annotation.id} variant="outlined" className="relative">
                {isEditing ? (
                  // Edit Mode
                  <div>
                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-[var(--text-0)]">Edit Annotation</h4>
                        <button
                          onClick={handleCancelEdit}
                          className="p-1 text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors"
                          title="Cancel"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="text-xs text-[var(--text-2)]">
                        <span className="font-mono text-[var(--accent)]">{annotation.linkedTo.type}:{annotation.linkedTo.id}</span>
                      </div>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <label className="block text-sm font-medium text-[var(--text-1)] mb-2">
                          Note Text
                        </label>
                        <textarea
                          value={noteText}
                          onChange={(e) => setNoteText(e.target.value)}
                          className="w-full px-3 py-3 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)] resize-none focus:outline-none focus:border-[var(--accent)] transition-colors"
                          rows={4}
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-[var(--text-1)] mb-2">
                          Tags
                        </label>
                        <input
                          type="text"
                          value={tags}
                          onChange={(e) => setTags(e.target.value)}
                          className="w-full px-3 py-2 text-sm bg-[var(--bg-2)] border border-[var(--stroke-0)] rounded text-[var(--text-0)] focus:outline-none focus:border-[var(--accent)] transition-colors"
                        />
                      </div>

                      <button
                        onClick={() => handleSaveEdit(annotation)}
                        disabled={!noteText.trim()}
                        className="w-full px-4 py-3 text-sm font-medium bg-[var(--good)] text-white rounded hover:bg-[var(--good-muted)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                      >
                        <Save className="w-4 h-4" />
                        Save Changes
                      </button>
                    </div>
                  </div>
                ) : (
                  // View Mode
                  <div>
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-mono text-[var(--accent)]">
                            {annotation.linkedTo.type}:{annotation.linkedTo.id}
                          </span>
                          <Timestamp value={annotation.timestamp} format="time" />
                        </div>
                        <div className="text-xs text-[var(--text-2)]">
                          By: <span className="text-[var(--text-1)]">{annotation.author}</span>
                        </div>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex items-center gap-2">
                        {onEdit && (
                          <button
                            onClick={() => handleEdit(annotation)}
                            className="p-2 text-[var(--text-2)] hover:text-[var(--accent)] hover:bg-[var(--bg-3)] rounded transition-colors"
                            title="Edit annotation"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                        )}
                        {onDelete && (
                          <button
                            onClick={() => handleDelete(annotation.id)}
                            className="p-2 text-[var(--text-2)] hover:text-[var(--bad)] hover:bg-[var(--bad-bg)] rounded transition-colors"
                            title="Delete annotation"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="text-sm text-[var(--text-0)] mb-3 leading-relaxed">
                      {annotation.text}
                    </div>

                    {annotation.tags && annotation.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {annotation.tags.map((tag, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 text-xs bg-[var(--bg-3)] border border-[var(--stroke-0)] rounded text-[var(--text-1)]"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })
        )}
      </div>
    </Card>
  );
}