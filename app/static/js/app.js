/* Amoja Harbor — shell interactions. */

document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebar-overlay");

    const closeSidebar = () => {
        if (!sidebar) return;
        sidebar.classList.remove("open");
        if (overlay) overlay.hidden = true;
    };

    const openSidebar = () => {
        if (!sidebar) return;
        sidebar.classList.add("open");
        if (overlay) overlay.hidden = false;
    };

    document.querySelectorAll("[data-sidebar-open]").forEach((button) => {
        button.addEventListener("click", openSidebar);
    });

    document.querySelectorAll("[data-sidebar-close]").forEach((button) => {
        button.addEventListener("click", closeSidebar);
    });

    overlay?.addEventListener("click", closeSidebar);

    document.querySelectorAll(".sidebar-nav a").forEach((link) => {
        link.addEventListener("click", closeSidebar);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeSidebar();
    });
});
