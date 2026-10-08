import { useState, useEffect } from 'react';
import { getImageUrl } from "../api/reportsApi";

/**
 * A secure image component that can handle ngrok browser warning headers
 */
export default function SecureImage({ src, alt, className, onError }) {
    const [imageSrc, setImageSrc] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    useEffect(() => {
        if (!src) {
            setLoading(false);
            return;
        }

        // Get the full URL (handling relative paths)
        const fullUrl = getImageUrl(src);

        if (!fullUrl) {
            setError(true);
            setLoading(false);
            return;
        }

        let isMounted = true;

        // Fetch with headers to bypass ngrok warning
        const fetchImage = async () => {
            try {
                setLoading(true);
                setError(false);

                const response = await fetch(fullUrl, {
                    headers: {
                        'ngrok-skip-browser-warning': 'true'
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to load image');
                }

                const blob = await response.blob();
                const objectUrl = URL.createObjectURL(blob);

                if (isMounted) {
                    setImageSrc(objectUrl);
                    setLoading(false);
                }
            } catch (err) {
                console.error("Error loading secure image:", err);
                if (isMounted) {
                    setError(true);
                    setLoading(false);
                }
            }
        };

        fetchImage();

        return () => {
            isMounted = false;
            // Clean up object URL when component unmounts or src changes
            if (imageSrc) {
                URL.revokeObjectURL(imageSrc);
            }
        };
    }, [src]);

    if (error) {
        if (onError) {
            // Create a fake event object for compatibility
            onError({ target: { style: {} } });
        }
        // If onError didn't handle it or wasn't provided, show fallback or nothing
        return (
            <div className={`${className} bg-gray-700 flex items-center justify-center text-gray-500 text-xs`}>
                Failed to load
            </div>
        );
    }

    if (loading) {
        return (
            <div className={`${className} bg-gray-800 animate-pulse flex items-center justify-center`}>
                <div className="w-6 h-6 border-2 border-gray-600 border-t-blue-500 rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <img
            src={imageSrc}
            alt={alt}
            className={className}
            onError={onError}
        />
    );
}
