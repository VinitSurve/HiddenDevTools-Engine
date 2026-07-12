from config import DM_TEMPLATE, RESOURCE_LINK, BRAND_NAME

class TemplateRenderer:
    @staticmethod
    def render_dm_template(username: str) -> str:
        """
        Renders the configured DM template with the required variables.
        """
        return DM_TEMPLATE.format(
            username=username,
            resource_link=RESOURCE_LINK,
            brand=BRAND_NAME
        )
