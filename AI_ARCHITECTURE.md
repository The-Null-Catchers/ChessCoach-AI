# AI Architecture

The AI coach is an explanatory layer, never the chess oracle. Its input contract will contain engine facts, board context, player rating band, detected motif candidates and allowed pedagogical detail. Providers will implement one typed interface for OpenAI, Gemini, Groq or local inference. Structured responses will be schema-validated and cached by position + concept + skill band + prompt version.
