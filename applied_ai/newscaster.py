from datetime import date
import json
import os
from pathlib import Path

import atoma
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
import requests


load_dotenv()


class Article:
    def __init__(self):
        self.title: str = str()
        self.content: str = str()
        self.link: str = str()


class AINewscaster:
    def __init__(self, interests: list, num_articles: int = 10):
        self.interests = interests
        self.num_articles = num_articles
        self.ai_client = OpenAI(api_key=os.environ.get('OPENAI'))

    def report_the_news(self):
        atom_feed = self.get_google_atom_feed()
        articles_content = self.get_articles_content(atom_feed)
        summarized_articles = self.summarize_articles(articles_content)
        newscast_script = self.write_newscast_script(summarized_articles)
        self.create_audio_newscast(newscast_script)

    def get_google_atom_feed(self) -> atoma.atom.AtomFeed:
        print("Fetching news articles...")
        todays_date = str(date.today())
        query = f"{' OR '.join(self.interests)}+after:{todays_date}"
        url = f'https://news.google.com/atom/search?cf=all&q={query}&hl=en-US&gl=US&ceid=US:en'
        response = requests.get(url)
        return atoma.parse_atom_bytes(response.content)

    def get_articles_content(self, atom_feed: atoma.atom.AtomFeed) -> list[Article]:
        print("Reading the articles...")
        articles = list()
        for entry in atom_feed.entries[:self.num_articles]:
            article = Article()
            article.title = entry.title.value
            article.link = entry.links[0].href

            fetched_content = requests.get(article.link).content.decode('utf-8')
            soup = BeautifulSoup(fetched_content, features='html.parser')
            try:
                cleaned_text = soup.article.text.strip()
            except:
                cleaned_text = soup.text.strip()
            article.content = cleaned_text

            articles.append(article)
        return articles

    def summarize_articles(self, articles: list[Article]) -> list[Article]:
        print("Summarizing the articles...")
        successful_summaries = list()
        for article in articles:
            try:
                summary = self.ai_summarize(article.content)
                if 'NOT ABLE TO ACCESS' in summary['summary'] + summary['title']:
                    continue
                similar = self.ensure_title_similarity(article.title, summary['title'])
                if similar.lower() == 'true':
                    article.content = summary
                    successful_summaries.append(article)
            except Exception as e:
                print('ERROR Occurred:', e)

        return successful_summaries

    def ai_summarize(self, content: str) -> dict:
        response = self.ai_client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": """Read the entire article.
                 Identify the key points. Rephrase in your own words.
                 Maintain the author's intent. Avoid summarizing cues. Keep it concise.
                 Check for completeness and accuracy. Revise for clarity and flow.
                 If you do not have access to the content, reply 'NOT ABLE TO ACCESS'"""},
                {"role": "user", "content": """Summarize this news article for me.
                 Respond in JSON format {'summary': <your_summary>,
                 'title': <your_succinct_title>} :""" + content}
            ]
        )
        return json.loads(response.choices[0].message.content)

    def ensure_title_similarity(self, original_title: str, summary_title: str) -> str:
        response = self.ai_client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": """Read both titles carefully.
                 Identify key themes and keywords.
                 Analyze context and subject matter.
                 Make a judgement as to whether the titles are the same subject or unrelated.
                 Report your findings in JSON format: {'related': <'true' or 'false'>}"""},
                {"role": "user", "content": f"Compare these two titles: 1. {original_title} & 2. {summary_title}"}
            ]
        )
        return json.loads(response.choices[0].message.content)['related']

    def write_newscast_script(self, articles: list[Article]) -> str:
        print("Writing your Newscaster's script...")
        content = '\n\n'.join([f"{a.title}\n{a.content}" for a in articles])

        response = self.ai_client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": """Thoroughly read the news articles.
                 structure the news script with an introduction, a body of stories,
                 and a conclusion. write a compelling introduction. develop the body
                 of the script where each story flows smoothly to the next.
                 Use a conversational tone. Avoid adding extra information.
                 Conclude each segment and the overall script.
                 Ensure clarity and brevity.
                 Do not include any cues or directives, just the words to be spoken.
                 The newscaster has no name, but speaks on behalf of 'Your Personalized News Source'"""},
                {"role": "user", "content": "Read the following articles as a news anchor would:" + content}
            ]
        )
        return response.choices[0].message.content

    def create_audio_newscast(self, script: str):
        print("Recording the Newscast...")
        speech_file_path = Path(__file__).parent / f"Newscast for {date.today()}.mp3"

        script = f"""
        {script}
        For your awareness, you're listening to an AI voice generated from a text-to-speech model.
        """

        response = self.ai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=script
        )

        response.stream_to_file(speech_file_path)
        print("Newscast created!")
        print("Saved to", speech_file_path)


if __name__ == "__main__":
    newscast = AINewscaster(
        interests=["AI", "Artificial Intelligence"],
        num_articles=5
    )
    newscast.report_the_news()
