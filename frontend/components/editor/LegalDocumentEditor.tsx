'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextAlign from '@tiptap/extension-text-align';
import Typography from '@tiptap/extension-typography';
import Placeholder from '@tiptap/extension-placeholder';
import { useEffect } from 'react';

interface LegalDocumentEditorProps {
  content: string;
  onChange: (content: string) => void;
  editable?: boolean;
  placeholder?: string;
}

const MenuBar = ({ editor }: any) => {
  if (!editor) {
    return null;
  }

  return (
    <div className="border-b border-border bg-muted/30 p-2 flex flex-wrap gap-1">
      {/* Text Formatting */}
      <div className="flex gap-1 pr-2 border-r border-border">
        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          disabled={!editor.can().chain().focus().toggleBold().run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('bold')
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Bold (Ctrl+B)"
        >
          <strong>B</strong>
        </button>
        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          disabled={!editor.can().chain().focus().toggleItalic().run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('italic')
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Italic (Ctrl+I)"
        >
          <em>I</em>
        </button>
        <button
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          disabled={!editor.can().chain().focus().toggleUnderline().run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('underline')
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Underline (Ctrl+U)"
        >
          <u>U</u>
        </button>
      </div>

      {/* Headings */}
      <div className="flex gap-1 pr-2 border-r border-border">
        <button
          onClick={() => editor.chain().focus().setParagraph().run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('paragraph')
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Paragraph"
        >
          P
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('heading', { level: 1 })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Heading 1"
        >
          H1
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('heading', { level: 2 })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Heading 2"
        >
          H2
        </button>
        <button
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('heading', { level: 3 })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Heading 3"
        >
          H3
        </button>
      </div>

      {/* Lists */}
      <div className="flex gap-1 pr-2 border-r border-border">
        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('bulletList')
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Bullet List"
        >
          •
        </button>
        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive('orderedList')
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Numbered List"
        >
          1.
        </button>
      </div>

      {/* Alignment */}
      <div className="flex gap-1 pr-2 border-r border-border">
        <button
          onClick={() => editor.chain().focus().setTextAlign('left').run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive({ textAlign: 'left' })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Align Left"
        >
          ⫷
        </button>
        <button
          onClick={() => editor.chain().focus().setTextAlign('center').run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive({ textAlign: 'center' })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Align Center"
        >
          ≡
        </button>
        <button
          onClick={() => editor.chain().focus().setTextAlign('right').run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive({ textAlign: 'right' })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Align Right"
        >
          ⫸
        </button>
        <button
          onClick={() => editor.chain().focus().setTextAlign('justify').run()}
          className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
            editor.isActive({ textAlign: 'justify' })
              ? 'bg-primary text-primary-foreground'
              : 'bg-background text-foreground hover:bg-muted'
          }`}
          title="Justify"
        >
          ≣
        </button>
      </div>

      {/* Actions */}
      <div className="flex gap-1">
        <button
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().chain().focus().undo().run()}
          className="px-3 py-1.5 text-sm font-medium rounded bg-background text-foreground hover:bg-muted disabled:opacity-50 transition-colors"
          title="Undo (Ctrl+Z)"
        >
          ↶
        </button>
        <button
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().chain().focus().redo().run()}
          className="px-3 py-1.5 text-sm font-medium rounded bg-background text-foreground hover:bg-muted disabled:opacity-50 transition-colors"
          title="Redo (Ctrl+Y)"
        >
          ↷
        </button>
      </div>
    </div>
  );
};

export default function LegalDocumentEditor({
  content,
  onChange,
  editable = true,
  placeholder = 'Start typing your legal document...',
}: LegalDocumentEditorProps) {
  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3],
        },
      }),
      Underline,
      TextAlign.configure({
        types: ['heading', 'paragraph'],
        alignments: ['left', 'center', 'right', 'justify'],
        defaultAlignment: 'left',
      }),
      Typography,
      Placeholder.configure({
        placeholder,
      }),
    ],
    content,
    editable,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: 'prose prose-sm sm:prose lg:prose-lg max-w-none focus:outline-none min-h-[600px] p-6',
      },
    },
  });

  // Update editor content when prop changes
  useEffect(() => {
    if (editor && content !== editor.getHTML()) {
      editor.commands.setContent(content);
    }
  }, [content, editor]);

  // Update editable state when prop changes
  useEffect(() => {
    if (editor) {
      editor.setEditable(editable);
    }
  }, [editable, editor]);

  if (!editor) {
    return null;
  }

  return (
    <div className="border border-border rounded-lg overflow-hidden bg-background">
      {editable && <MenuBar editor={editor} />}
      <EditorContent editor={editor} className="legal-document-editor" />
    </div>
  );
}
