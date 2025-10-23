// Image error handling
function handleImageError(img) {
    console.error('Failed to load image:', img.src);
    // Add a visible error message
    const errorDiv = document.createElement('div');
    errorDiv.className = 'image-error-message';
    errorDiv.innerHTML = `
        <p>❌ Failed to load image</p>
        <p style="font-size: 0.9rem; color: var(--secondary);">
            Please try refreshing the page
        </p>
    `;
    img.parentNode.insertBefore(errorDiv, img.nextSibling);
    
    // Add error styling to the image
    img.style.opacity = '0.5';
    img.style.border = '2px solid var(--danger)';
}