'use client';

/**
 * Document Upload Page
 *
 * Upload documents to a case with drag-and-drop support.
 */

import { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { AppLayout } from '@/components/layout/AppLayout';
import { documentsAPI } from '@/lib/api/services';
import type { Document } from '@/types/api';

export default function UploadDocumentsPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const [uploadedDocs, setUploadedDocs] = useState<Document[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    if (e.dataTransfer.files) {
      const newFiles = Array.from(e.dataTransfer.files);
      setFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);
    const newErrors: Record<string, string> = {};
    const uploaded: Document[] = [];

    for (const file of files) {
      try {
        setUploadProgress((prev) => ({ ...prev, [file.name]: 50 }));

        const doc = await documentsAPI.upload(caseId, file);
        uploaded.push(doc);

        setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
      } catch (err) {
        newErrors[file.name] = err instanceof Error ? err.message : 'Upload failed';
        setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
      }
    }

    setErrors(newErrors);
    setUploadedDocs(uploaded);
    setUploading(false);

    // If all succeeded, redirect back to case
    if (Object.keys(newErrors).length === 0) {
      setTimeout(() => {
        router.push(`/cases/${caseId}`);
      }, 1500);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Upload Documents</h1>
          <p className="mt-1 text-sm text-gray-600">
            Upload PDF documents to be processed and indexed for this case.
          </p>
        </div>

        {/* Drag and Drop Area */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`relative border-2 border-dashed rounded-lg p-12 text-center ${
            isDragging
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 bg-white'
          }`}
        >
          <input
            type="file"
            id="file-upload"
            multiple
            accept=".pdf"
            onChange={handleFileChange}
            className="sr-only"
            disabled={uploading}
          />

          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          <p className="mt-2 text-sm text-gray-600">
            <label
              htmlFor="file-upload"
              className="relative cursor-pointer rounded-md font-medium text-blue-600 hover:text-blue-500"
            >
              Click to upload
            </label>
            {' or drag and drop'}
          </p>
          <p className="mt-1 text-xs text-gray-500">PDF files only</p>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Selected Files ({files.length})
              </h3>

              <ul className="divide-y divide-gray-200">
                {files.map((file, index) => (
                  <li key={index} className="py-3 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.name}
                      </p>
                      <p className="text-sm text-gray-500">
                        {formatFileSize(file.size)}
                      </p>

                      {uploadProgress[file.name] !== undefined && (
                        <div className="mt-2">
                          {uploadProgress[file.name] === 100 ? (
                            <span className="text-xs text-green-600">Uploaded</span>
                          ) : uploadProgress[file.name] > 0 ? (
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-600 h-2 rounded-full transition-all"
                                style={{ width: `${uploadProgress[file.name]}%` }}
                              />
                            </div>
                          ) : null}

                          {errors[file.name] && (
                            <p className="text-xs text-red-600 mt-1">
                              {errors[file.name]}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {!uploading && (
                      <button
                        onClick={() => removeFile(index)}
                        className="ml-4 text-sm text-red-600 hover:text-red-800"
                      >
                        Remove
                      </button>
                    )}
                  </li>
                ))}
              </ul>

              <div className="mt-6 flex items-center justify-end space-x-3">
                <button
                  onClick={() => router.push(`/cases/${caseId}`)}
                  disabled={uploading}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={uploadFiles}
                  disabled={uploading || files.length === 0}
                  className="px-4 py-2 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {uploading ? 'Uploading...' : `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Success Message */}
        {uploadedDocs.length > 0 && Object.keys(errors).length === 0 && (
          <div className="rounded-md bg-green-50 p-4">
            <div className="flex">
              <div className="ml-3">
                <p className="text-sm font-medium text-green-800">
                  Successfully uploaded {uploadedDocs.length} document{uploadedDocs.length !== 1 ? 's' : ''}!
                </p>
                <p className="mt-1 text-sm text-green-700">
                  Redirecting back to case...
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
