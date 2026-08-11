document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('#loginForm');
    const brandPanel = document.querySelector('.brand-panel');
    const password = document.querySelector('#id_password');
    const passwordToggle = document.querySelector('#passwordToggle');
    const continueButton = document.querySelector('#continueButton');

    const pointerMotionAllowed = window.matchMedia(
        '(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)'
    );

    if (brandPanel && pointerMotionAllowed.matches) {
        let frameId = null;
        let currentX = brandPanel.clientWidth / 2;
        let currentY = brandPanel.clientHeight / 2;
        let targetX = currentX;
        let targetY = currentY;

        const renderPointerMotion = () => {
            const width = brandPanel.clientWidth;
            const height = brandPanel.clientHeight;
            const normalizedX = (currentX / width - 0.5) * 2;
            const normalizedY = (currentY / height - 0.5) * 2;

            brandPanel.style.setProperty('--pointer-x', `${currentX}px`);
            brandPanel.style.setProperty('--pointer-y', `${currentY}px`);
            brandPanel.style.setProperty('--dot-x', `${normalizedX * 8}px`);
            brandPanel.style.setProperty('--dot-y', `${normalizedY * 8}px`);
            brandPanel.style.setProperty('--logo-x', `${normalizedX * 2.5}px`);
            brandPanel.style.setProperty('--logo-y', `${normalizedY * 2.5}px`);
            brandPanel.style.setProperty('--message-x', `${normalizedX * 9}px`);
            brandPanel.style.setProperty('--message-y', `${normalizedY * 6}px`);
        };

        const animatePointerMotion = () => {
            currentX += (targetX - currentX) * 0.14;
            currentY += (targetY - currentY) * 0.14;
            renderPointerMotion();

            const stillMoving = Math.abs(targetX - currentX) > 0.1 || Math.abs(targetY - currentY) > 0.1;
            if (stillMoving) {
                frameId = window.requestAnimationFrame(animatePointerMotion);
            } else {
                frameId = null;
            }
        };

        const startAnimation = () => {
            if (frameId === null) {
                frameId = window.requestAnimationFrame(animatePointerMotion);
            }
        };

        brandPanel.addEventListener('pointerenter', (event) => {
            const bounds = brandPanel.getBoundingClientRect();
            targetX = event.clientX - bounds.left;
            targetY = event.clientY - bounds.top;
            brandPanel.classList.add('is-pointer-active');
            startAnimation();
        });

        brandPanel.addEventListener('pointermove', (event) => {
            const bounds = brandPanel.getBoundingClientRect();
            targetX = event.clientX - bounds.left;
            targetY = event.clientY - bounds.top;
            startAnimation();
        });

        brandPanel.addEventListener('pointerleave', () => {
            targetX = brandPanel.clientWidth / 2;
            targetY = brandPanel.clientHeight / 2;
            brandPanel.classList.remove('is-pointer-active');
            startAnimation();
        });
    }

    passwordToggle?.addEventListener('click', () => {
        const isVisible = password.type === 'text';
        password.type = isVisible ? 'password' : 'text';
        passwordToggle.textContent = isVisible ? 'Show' : 'Hide';
        passwordToggle.setAttribute('aria-pressed', String(!isVisible));
        password.focus({ preventScroll: true });
    });

    form?.addEventListener('submit', (event) => {
        if (!form.checkValidity()) {
            event.preventDefault();
            form.reportValidity();
            return;
        }

        continueButton.disabled = true;
        continueButton.classList.add('is-loading');
        continueButton.setAttribute('aria-busy', 'true');
        continueButton.querySelector('.button-label').textContent = 'Signing in';
    });
});
