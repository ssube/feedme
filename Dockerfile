FROM python:3.10

WORKDIR /feedme

COPY requirements/cpu.txt /feedme/requirements/cpu.txt
RUN pip install --no-cache-dir -r requirements/cpu.txt

COPY requirements/base.txt /feedme/requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt
RUN pip install --no-cache-dir --index-url https://test.pypi.org/simple/ packit_llm==0.1.0

COPY feedme/ /feedme/feedme/

CMD ["python", "-m", "feedme.multi_post"]
