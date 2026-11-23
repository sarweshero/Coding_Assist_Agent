import litellm

from app.config_manager import config_manager


class LLMRouter:
    def get_model(self, agent_name: str) -> str:
        return config_manager.get_model(agent_name)

    async def complete(
        self,
        agent_name: str,
        system_prompt: str,
        user_content: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> str:
        response = await litellm.acompletion(
            model=self.get_model(agent_name),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


llm = LLMRouter()
