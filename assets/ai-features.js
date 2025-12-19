// AI Features JavaScript
// Handles client-side interactions for AI components

// Copy email to clipboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Listen for clicks on copy email button
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'copy-email-btn') {
            e.preventDefault();
            
            // Get email subject and body
            const subject = document.getElementById('email-subject-edit')?.value || '';
            const body = document.getElementById('email-body-edit')?.value || '';
            
            // Combine into full email text
            const fullEmail = `Subject: ${subject}\n\n${body}`;
            
            // Copy to clipboard
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(fullEmail)
                    .then(() => {
                        console.log('Email copied to clipboard');
                    })
                    .catch(err => {
                        console.error('Failed to copy email:', err);
                        // Fallback to older method
                        fallbackCopyTextToClipboard(fullEmail);
                    });
            } else {
                // Fallback for older browsers
                fallbackCopyTextToClipboard(fullEmail);
            }
        }
    });
});

// Fallback copy function for older browsers
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '-9999px';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            console.log('Fallback: Email copied to clipboard');
        } else {
            console.error('Fallback: Failed to copy email');
        }
    } catch (err) {
        console.error('Fallback: Failed to copy email', err);
    }
    
    document.body.removeChild(textArea);
}
